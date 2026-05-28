#!/usr/bin/env bash
#
# snapshot_fixtures.sh — capture a public job-application page as a
# self-hosted, PII-scrubbed snapshot for the harness.
#
# Per PITFALLS.md #8 (public-fixture rot) and CONTEXT.md "Fixtures —
# self-hosted snapshots", the bench MUST drive MCPs against
# 127.0.0.1:8765 instead of live URLs. This script is the capture half
# (serve_fixtures.sh is the serve half).
#
# Usage:
#   scripts/snapshot_fixtures.sh <platform> <source_url> [date]
#
#   platform     greenhouse | ashby
#   source_url   the live page to mirror (must currently return 200)
#   date         optional override (default: $(date -u +%Y-%m-%d))
#
# Behaviour:
#   1. Refuse if fixtures/snapshots/<platform>_<date>/ already exists
#      (no silent re-capture — drift would be invisible). To re-capture,
#      `rm -rf` the dir manually.
#   2. wget --mirror with a desktop Chrome UA so the target serves the
#      same HTML a real browser would receive.
#   3. PII scrub: aggressive sed substitution of any two-word
#      capitalized string with the mock applicant "Jane Testworth".
#      Belt-and-suspenders — bench/scrub_artifacts.py is the post-check.
#   4. Compute a deterministic directory SHA256 over the served-content
#      tree (excluding the .sha256 file itself so the digest is stable
#      across re-computations).
#   5. Write PROVENANCE.md with source URL, capture date + UTC time,
#      wget version, scrub-substitution count, and the directory hash.
#
# Idempotency: the script bails on existing output. PROVENANCE.md is
# written from a known template — re-runs against a fresh empty dir
# produce a byte-identical PROVENANCE.md (modulo the timestamp + hash).
#
# Exit codes:
#   0 — capture succeeded; PROVENANCE.md written
#   1 — bad args, output dir already exists, wget failure, or empty mirror
#
# Notes:
#   - macOS Homebrew wget 1.21+ assumed (verified by scripts/check_prereqs.sh).
#   - BSD sed in-place flag uses `-i.bak` then deletes the .bak files
#     so the script is portable to GNU sed without changes.
#   - SPA gotcha: wget --mirror does NOT capture runtime API responses.
#     Ashby (React SPA) will likely capture only the empty <div id="root">
#     shell. This is acceptable for Phase 1 — the snapshot IS what wget
#     gets, and the harness records that as the reproducibility surface.
#     The byte-count + DOM-structure note in PROVENANCE.md surfaces this.

set -euo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

usage() {
    cat >&2 <<EOF
usage: $0 <platform> <source_url> [date]

  platform     greenhouse | ashby
  source_url   live URL to mirror (must currently return 200)
  date         optional override (default: \$(date -u +%Y-%m-%d))

example:
  $0 greenhouse https://job-boards.greenhouse.io/anthropic/jobs/5023394008
EOF
    exit 1
}

if [[ $# -lt 2 || $# -gt 3 ]]; then
    usage
fi

PLATFORM="$1"
URL="$2"
DATE="${3:-$(date -u +%Y-%m-%d)}"

case "$PLATFORM" in
    greenhouse|ashby) ;;
    *)
        echo "snapshot_fixtures: unknown platform '$PLATFORM' (expected: greenhouse|ashby)" >&2
        exit 1
        ;;
esac

if ! command -v wget >/dev/null 2>&1; then
    echo "snapshot_fixtures: wget not found — install via 'brew install wget'" >&2
    exit 1
fi

OUTDIR="$REPO_ROOT/fixtures/snapshots/${PLATFORM}_${DATE}"
if [[ -e "$OUTDIR" ]]; then
    echo "snapshot_fixtures: snapshot already exists at $OUTDIR" >&2
    echo "snapshot_fixtures: rm -rf '$OUTDIR' to re-capture" >&2
    exit 1
fi

mkdir -p "$OUTDIR"

WGET_VERSION=$(wget --version | head -1)
CAPTURE_TS_UTC=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# wget --mirror flags:
#   --convert-links     rewrite hrefs to relative paths so the mirror serves
#                       standalone (no live-internet round-trips)
#   --adjust-extension  ensure .html on text/html responses
#   --page-requisites   inline images, css, js needed to render the page
#   --no-parent         don't ascend above the URL path
#   --execute robots=off  job-board sites often serve robots.txt that blocks
#                         mirror; we're capturing a public page for archival
#   --user-agent=...    desktop Chrome so the target returns the real HTML
#                       (some ATSes serve a minimal stub to non-browser UAs)
#   --no-host-directories  drop the host name from the dir structure so the
#                          mirror is host-portable
#   --tries=2 --timeout=30  fail fast on dead URLs
echo "==> wget --mirror $URL"
echo "==> output: $OUTDIR"
set +e
wget \
    --mirror \
    --convert-links \
    --adjust-extension \
    --page-requisites \
    --no-parent \
    --no-host-directories \
    --execute robots=off \
    --user-agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36' \
    --tries=2 \
    --timeout=30 \
    --directory-prefix="$OUTDIR" \
    "$URL" \
    > "$OUTDIR/.wget.log" 2>&1
WGET_RC=$?
set -e

# wget mirror returns 8 for "server issued an error" on linked assets
# (e.g. 404 on a tracking pixel). That's not fatal for our purposes;
# only rc=1,2,3,4,5,6,7 are hard failures. rc=0 means clean, rc=8
# means "some asset failed but the main page is there".
if [[ "$WGET_RC" -ne 0 && "$WGET_RC" -ne 8 ]]; then
    echo "snapshot_fixtures: wget failed (rc=$WGET_RC) for $URL" >&2
    echo "----- wget log tail -----" >&2
    tail -20 "$OUTDIR/.wget.log" >&2
    echo "-------------------------" >&2
    exit 1
fi

# Verify the mirror produced something usable (any HTML at all).
HTML_COUNT=$(find "$OUTDIR" -type f \( -name '*.html' -o -name '*.htm' \) | wc -l | tr -d ' ')
if [[ "$HTML_COUNT" -eq 0 ]]; then
    echo "snapshot_fixtures: mirror produced zero HTML files for $URL" >&2
    echo "----- wget log tail -----" >&2
    tail -20 "$OUTDIR/.wget.log" >&2
    echo "-------------------------" >&2
    exit 1
fi

# PII scrub. Aggressive: any two-word capitalized string becomes the mock.
# This is intentional — bench/scrub_artifacts.py is the post-check that
# catches anything we miss.
#
# Implementation note: BSD sed lacks Python-style \b word boundaries.
# That matters because NAME_REGEX in scrub_artifacts.py uses \b...\b,
# and HTML-encoded entities like `>Jane` look like a single word to
# Python's \b (the `e` and `J` are both word chars, so \b fails), while
# BSD sed's `[A-Z][a-z]+ [A-Z][a-z]+` would happily replace it. The two
# views diverge and leave residue scrub_artifacts.py rejects.
#
# Fix: do the scrub in Python with the EXACT NAME_REGEX from
# bench/scrub_artifacts.py, iterating until convergence. We embed the
# regex literal here rather than importing the module so the script
# stays self-contained (and survives a future rename of the module).
echo "==> PII scrub (NAME_REGEX-aligned, iterates to convergence)"
VENV_PY="$REPO_ROOT/.venv/bin/python"
if [[ ! -x "$VENV_PY" ]]; then
    echo "snapshot_fixtures: project venv python missing at $VENV_PY" >&2
    echo "snapshot_fixtures: run 'uv sync' first" >&2
    exit 1
fi

SCRUB_COUNT=$(
    "$VENV_PY" - "$OUTDIR" <<'PYEOF'
import re
import sys
from pathlib import Path

# Keep this regex in lock-step with bench/scrub_artifacts.py NAME_REGEX.
NAME_REGEX = re.compile(r"\b[A-Z][a-z]+ [A-Z][a-z]+(?:-[A-Z][a-z]+)?\b")
ALLOW = {"Jane Testworth"}
EXTS = {".html", ".htm", ".js", ".json"}

root = Path(sys.argv[1])
total_subs = 0

for path in sorted(root.rglob("*")):
    if not path.is_file() or path.suffix.lower() not in EXTS:
        continue
    text = path.read_text(encoding="utf-8", errors="replace")
    # Count pre-scrub non-allow-listed matches.
    pre_matches = [m for m in NAME_REGEX.findall(text) if m not in ALLOW]
    total_subs += len(pre_matches)
    # Iterate substitution to convergence (cap at 8 rounds for safety;
    # in practice every test input converges in 1-3).
    for _ in range(8):
        # Substitute only matches NOT in the allow-list. We do this by
        # using a callable so the allow-listed name is preserved verbatim.
        new_text = NAME_REGEX.sub(
            lambda m: m.group(0) if m.group(0) in ALLOW else "Jane Testworth",
            text,
        )
        if new_text == text:
            break
        text = new_text
    path.write_text(text, encoding="utf-8")

print(total_subs)
PYEOF
)

if [[ -z "$SCRUB_COUNT" ]]; then
    echo "snapshot_fixtures: PII scrub failed to report a count — aborting" >&2
    exit 1
fi

# Compute a deterministic directory SHA256.
#
# We deliberately do NOT tar the directory: BSD tar embeds mtime/uid/gid
# metadata in the archive headers, which makes the resulting SHA256 vary
# across re-captures even when the on-disk content is byte-identical.
# That kills the entire point of the digest.
#
# Instead, we hash each file's content + relative path, sorted, then hash
# the concatenation. The result depends only on (filenames + their bytes)
# and is reproducible across machines and across re-captures of the same
# upstream content.
#
# Excludes:
#   - .sha256        (chicken-and-egg)
#   - .wget.log      (wall-clock timestamps + per-request progress; also
#                     gets deleted at the end of this script)
#   - PROVENANCE.md  (contains the hash itself + capture timestamp)
#
# LC_ALL=C on the sort guarantees byte-order rather than locale-dependent
# ordering — without it a macOS-vs-Linux byte differential could shift
# the file ordering and change the digest.
echo "==> compute directory SHA256"
SHA256=$(
    cd "$OUTDIR" && \
    find . -type f \
        ! -name '.sha256' ! -name '.wget.log' ! -name 'PROVENANCE.md' \
        -print0 \
        | LC_ALL=C sort -z \
        | xargs -0 shasum -a 256 \
        | shasum -a 256 \
        | awk '{print $1}'
)
echo "$SHA256  ${PLATFORM}_${DATE}" > "$OUTDIR/.sha256"

# Total served-content byte count (excluding the meta files above).
BYTE_COUNT=$(
    find "$OUTDIR" -type f \
        ! -name '.sha256' ! -name '.wget.log' ! -name 'PROVENANCE.md' \
        -exec wc -c {} \; \
        | awk '{sum += $1} END {print sum+0}'
)
FILE_COUNT=$(
    find "$OUTDIR" -type f \
        ! -name '.sha256' ! -name '.wget.log' ! -name 'PROVENANCE.md' \
        | wc -l | tr -d ' '
)

# DOM-structure note for the PROVENANCE.md (Ashby-SPA caveat surfacing).
# Pick the largest .html file as the "primary" page.
PRIMARY_HTML=$(
    find "$OUTDIR" -type f \( -name '*.html' -o -name '*.htm' \) \
        -exec wc -c {} \; \
        | sort -rn | head -1 | awk '{print $2}'
)
PRIMARY_BYTES=0
PRIMARY_REL=""
if [[ -n "$PRIMARY_HTML" ]]; then
    PRIMARY_BYTES=$(wc -c < "$PRIMARY_HTML" | tr -d ' ')
    PRIMARY_REL=${PRIMARY_HTML#"$OUTDIR/"}
fi
# Detect the React-SPA-shell pattern. Two indicators:
#   1. A `<div id="root">` mount point (Ashby + most React apps).
#   2. The body lacks substantive text outside of <script>, <style>, and
#      loading-spinner CSS.
# We don't try to render JS to check for hydration — the static HTML
# either has the job content baked in or it doesn't. Ashby's shell ships
# a loading-spinner CSS block inside the root <div> but no posting body;
# Greenhouse SSRs the full posting HTML into the body. Heuristic:
# if the file matches the root-mount pattern AND has a `<noscript>You
# need to enable JavaScript</noscript>` banner, call it a SPA shell.
SPA_SHELL_NOTE=""
if [[ -n "$PRIMARY_HTML" ]]; then
    if grep -q '<div id="root"' "$PRIMARY_HTML" 2>/dev/null \
       && grep -q 'enable JavaScript' "$PRIMARY_HTML" 2>/dev/null; then
        SPA_SHELL_NOTE="**SPA-shell detected:** primary HTML contains a \`<div id=\"root\">\` mount point and a \`<noscript>You need to enable JavaScript</noscript>\` banner, indicating no server-rendered listing content. wget --mirror cannot capture the runtime-fetched API responses that hydrate this SPA; the harness will see the shell (and the loading-spinner CSS) only. Acceptable for Phase 1 — this IS the reproducibility surface, and the snapshot is what every MCP gets measured against. The recording-proxy fix is deferred per CONTEXT.md scope cut."
    fi
fi

# Write PROVENANCE.md from the template.
#
# Heading is intentionally NOT two-word title-case ("Snapshot provenance",
# not "Snapshot Provenance") so it doesn't trip bench/scrub_artifacts.py's
# NAME_REGEX (which flags any "[A-Z][a-z]+ [A-Z][a-z]+" pair). The scrub
# script is intentionally conservative; matching the regex with a literal
# allow-list of doc strings would invite drift. Reword instead.
cat > "$OUTDIR/PROVENANCE.md" <<EOF
# Snapshot provenance — ${PLATFORM}_${DATE}

- **Source URL:** ${URL}
- **Capture date:** ${DATE} (UTC)
- **Capture timestamp:** ${CAPTURE_TS_UTC}
- **Capture tool:** ${WGET_VERSION}
- **Captured by:** scripts/snapshot_fixtures.sh
- **Scrubbing applied:**
  - Two-word capitalized strings replaced with \`Jane Testworth\` using the
    same \`NAME_REGEX\` as \`bench/scrub_artifacts.py\`, iterated to convergence.
  - Count of pre-scrub non-allow-listed matches: ${SCRUB_COUNT}
  - Allow-list deltas: none
- **Directory SHA256:** ${SHA256}  ${PLATFORM}_${DATE}
- **Files captured:** ${FILE_COUNT}
- **Total bytes (served content):** ${BYTE_COUNT}
- **Primary HTML:** \`${PRIMARY_REL}\` (${PRIMARY_BYTES} bytes)
- **Reason for capture:** Pitfall 8 (public-fixture rot) — live URLs 404 within 6 months. This snapshot is the test target; live-URL drift is a separate daily-smoke gate (deferred to G-710).
- **Drift detection:** ONE live-URL smoke test per platform — \`make smoke-live\` (diagnostic only, not part of the scored bench flow).
EOF

if [[ -n "$SPA_SHELL_NOTE" ]]; then
    cat >> "$OUTDIR/PROVENANCE.md" <<EOF

## SPA-shell caveat

${SPA_SHELL_NOTE}
EOF
fi

# Delete the wget log on success — it contains absolute paths
# (e.g. /Users/<username>/...) that would leak machine identifiers to a
# public repo. The log is useful only when wget fails; on the happy path
# the captured files themselves are the evidence.
rm -f "$OUTDIR/.wget.log"

# Final post-check — bench/scrub_artifacts.py must report clean.
# We don't invoke it here (caller does in the orchestration script) so
# the script stays small and shell-only. Surface the path to remind the
# caller.
echo "==> snapshot captured at $OUTDIR"
echo "==> next: uv run python -m bench.scrub_artifacts '$OUTDIR'"

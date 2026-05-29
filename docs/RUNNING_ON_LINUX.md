# Running the harness on Linux (G-737 reproducer)

This is the recipe used for the Obscura Linux A/B captured in `results/2026-05-29-linux/`. Different from the macOS `docs/REPRODUCIBILITY.md` recipe — Linux has several portability gotchas that v1.0 didn't surface.

## Why this exists

v1.0 was developed and scored on macOS arm64. Two findings from the v1.0.x cross-platform investigation make this Linux recipe necessary:

1. **Harness `ulimit -v 4194304` (4 GB virtual address space) is enforced strictly on Linux.** Node 22's V8 pointer-compression sandbox alone reserves ~4 GB virtual space on startup, so any Node-based MCP child crashes immediately with `WebAssembly.instantiate(): Out of memory` under the v1.0 ulimit on Linux. On macOS the same ulimit was tolerant. **Fix: raise to 16 GB or drop, locally for the Linux run.**
2. **`obscura serve` has a phantom-listener bug on Linux x86_64.** Even with the ulimit fix, Obscura's engine logs that it's listening on `ws://127.0.0.1:9222` but the port is never actually bound. See `results/2026-05-29-linux/obscura/DEEP_ANALYSIS.md` for the bisection.

## Host requirements

- Linux x86_64 with ≥ 4 GB free RAM
- Docker (29.x verified; 24.x+ likely fine)
- Outbound internet access (Docker pulls images, container fetches Node + Python packages)
- Loopback `127.0.0.1:8765` available for the fixture server
- An Anthropic API key (for Claude Code orchestration if running the full harness)

## Recipe

### 1. Clone repo + build container

```bash
git clone https://github.com/pleasedodisturb/web-agent-comparison
cd web-agent-comparison

# Write the Dockerfile (or copy from this repo)
cat > Dockerfile.harness <<'EOF'
FROM node:22-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 python3-pip python3-venv \
      jq curl ca-certificates gettext-base bash procps psmisc \
      libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 libxcomposite1 \
      libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 \
      libcairo2 libasound2 fonts-liberation lsof \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --break-system-packages uv==0.7.13
RUN npm install -g @anthropic-ai/claude-code
RUN npm install -g obscura-mcp@0.1.4-3
WORKDIR /work
CMD ["/bin/bash"]
EOF

sudo docker build -f Dockerfile.harness -t web-agent-harness:linux .
```

### 2. Apply Linux-local harness patch (raise ulimit)

```bash
cp scripts/run_mcp_session.sh scripts/run_mcp_session.sh.macos-original
sed -i '/^ulimit -v 4194304/c\
ulimit -v 16777216 2>/dev/null || \\\
    echo "run_mcp_session: ulimit -v unsupported on this platform (skipping)" >&2' \
    scripts/run_mcp_session.sh
```

**This is a local-only patch. DO NOT commit `scripts/run_mcp_session.sh` back upstream from the Linux machine** — the macOS-locked harness invariant is one of the v1.0 sacrosanct properties. Restore the original before any git push:

```bash
cp scripts/run_mcp_session.sh.macos-original scripts/run_mcp_session.sh
```

### 3. Ship Anthropic key transiently (for Claude Code orchestrator)

Out-of-band on your Mac:

```bash
# 1. Pull key from local secret store
rbw get 'Anthropic Claude' --field Anthropic_API | \
    ssh <linux-host> 'umask 077; cat > $HOME/.anth-key-tmp && chmod 600 $HOME/.anth-key-tmp'

# 2. Verify on linux-host: stat shows perms=600
ssh <linux-host> 'stat -c "perms=%a len=%s" ~/.anth-key-tmp'
```

The key file is consumed inline by `docker run -e ANTHROPIC_API_KEY=$(cat ~/.anth-key-tmp)`. After the benchmark, `shred -u ~/.anth-key-tmp` to remove it.

### 4. Run a single MCP pass

Inside the container, sequence is: `uv sync --frozen` → start fixture server (handled by harness) → `bash scripts/run_mcp_session.sh <mcp>` → captures evidence to `results/<DATE>/<mcp>/`.

```bash
cat > /tmp/pass.sh <<'EOF'
set +e
cd /work
uv sync --frozen 2>&1 | tail -3
.venv/bin/python --version
# (overlay a Linux-specific .mcp.json if needed; e.g., obscura with --stealth)
cp results/<DATE>-linux/mcp.linux.json .mcp.json  # if overlay exists
bash scripts/run_mcp_session.sh <mcp> 2>&1 | tee /tmp/harness.log
EOF

sudo docker run --rm --init --network host \
  --user $(id -u):$(id -g) \
  -e HOME=/tmp \
  -e ANTHROPIC_API_KEY="$(cat ~/.anth-key-tmp)" \
  -v $PWD:/work \
  -v /tmp/pass.sh:/pass.sh \
  web-agent-harness:linux \
  bash /pass.sh
```

After the run, move output to a Linux-evidence subdir:

```bash
TODAY=$(date -u +%Y-%m-%d)
mkdir -p results/${TODAY}-linux/<mcp>/PASS1
mv results/${TODAY}/<mcp>/* results/${TODAY}-linux/<mcp>/PASS1/
rmdir results/${TODAY}/<mcp>
```

### 5. Cleanup

```bash
shred -u ~/.anth-key-tmp                          # remove transient key
git checkout -- scripts/run_mcp_session.sh        # restore canonical harness
rm -f scripts/run_mcp_session.sh.macos-original   # remove backup
sudo docker image prune -f                        # optional, recovers ~2 GB
```

`git checkout` is preferred over `cp` here so any other local edits to the harness raise a merge conflict instead of being silently overwritten.

## Per-MCP Linux notes

| MCP | Linux status as of 2026-05-29 |
|-----|-------------------------------|
| playwright | Not yet re-tested on Linux. Likely works with the ulimit fix. |
| browser-use (direct) | Not yet re-tested. Likely works with the ulimit fix. |
| browser-use (agent) | **Broken on both Linux and macOS** — see browser-use/browser-use#4846 (v0.12.7 MCP-agent CDP bug). |
| chrome-devtools-mcp | Not yet re-tested. Likely works with the ulimit fix. |
| lightpanda | Not yet re-tested. Zig binary; should work natively. |
| obscura | **Broken on Linux x86_64** — engine binary has phantom-listener bug; `obscura serve` logs port 9222 binding but never actually opens it. Documented in `results/2026-05-29-linux/obscura/DEEP_ANALYSIS.md`. |
| firecrawl | Cloud-only; works from Linux as long as `FIRECRAWL_API_KEY` is in env. |
| cloakbrowser | Closed-source binary, macOS aarch64 verified, **Linux availability unknown** — would need a separate G-710 work item. |

## Known gaps

- v1.0.x is the first cross-platform investigation; only Obscura was tested on Linux (because G-737 specifically targeted it).
- The harness's `ulimit -v` portability fix is documented here but **not patched in the committed scripts** — a future v1.1 or v2.0 milestone should integrate an OS-detecting ulimit.
- TLS fingerprint capture on Linux is straightforward (curl-based or via any working MCP) but has not been done; it's tracked in `#11`/G-739.

## See also

- `docs/REPRODUCIBILITY.md` — the macOS reproducer (v1.0 canonical)
- `results/2026-05-29-linux/obscura/DEEP_ANALYSIS.md` — what the Obscura Linux A/B actually found
- GitHub `#9` / Linear `G-737` — Obscura Linux A/B tracking

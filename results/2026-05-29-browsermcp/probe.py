#!/usr/bin/env python3
"""Direct JSON-RPC walker for BrowserMCP — S1+S2 + TLS fingerprint capture.

Architecture: mcp-server-browsermcp binds WebSocket port 9009 for the Chrome
extension. The MCP server kills any prior process on 9009, so the extension
must (re-)connect AFTER this server starts. We give it a 30-second window.

Captures: tool inventory, navigate/snapshot S1+S2 against loopback fixtures,
plus a TLS fingerprint capture against tools.scrapfly.io/api/fp/ja3?extended=1
(which captures the user's REAL Chrome handshake — the production baseline).
"""
import json
import subprocess
import sys
import time
from datetime import datetime, timezone

FIXTURE_SERVER = "http://127.0.0.1:8765"
FIXTURES = {
    # discovered from the screenshot: fixtures live under dated subdirs
    "S1_greenhouse": f"{FIXTURE_SERVER}/greenhouse_2026-05-22/",
    "S2_ashby":      f"{FIXTURE_SERVER}/ashby_2026-05-22/",
}
TLS_PROBE_URL = "https://tools.scrapfly.io/api/fp/ja3?extended=1"

events = []
def log(event_type, **payload):
    events.append({
        "t": datetime.now(timezone.utc).isoformat(),
        "type": event_type,
        **payload,
    })
    sys.stdout.write(f"[{event_type}] {json.dumps(payload, default=str)[:250]}\n")
    sys.stdout.flush()

def send(proc, msg):
    proc.stdin.write(json.dumps(msg) + "\n")
    proc.stdin.flush()

def recv(proc):
    line = proc.stdout.readline()
    return json.loads(line) if line else None

def call_tool(proc, msg_id, name, args=None):
    send(proc, {"jsonrpc": "2.0", "id": msg_id, "method": "tools/call",
                "params": {"name": name, "arguments": args or {}}})
    return recv(proc)

def main():
    # stderr is piped to a companion file so we can see vendor errors
    # (e.g., the recursive server.close stack overflow on shutdown)
    # without polluting the events log on stdout.
    stderr_log = open("results/2026-05-29-browsermcp/probe.stderr.log", "w")
    proc = subprocess.Popen(
        ["mcp-server-browsermcp"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=stderr_log,
        text=True, bufsize=1,
    )
    try:
        # 1. Initialize
        send(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                    "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                               "clientInfo": {"name": "exploratory-probe", "version": "0.1"}}})
        init = recv(proc)
        log("initialize", result=init.get("result", {}).get("serverInfo"))
        send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})
        time.sleep(0.3)

        # 2. Tool list (always works regardless of Chrome connection)
        send(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        tools = recv(proc)
        tool_names = [t["name"] for t in tools.get("result", {}).get("tools", [])]
        log("tools_list", count=len(tool_names), names=tool_names)

        # 3. Hold for Chrome extension handshake — server is now on port 9009.
        # Poll browser_navigate against a dummy URL until "No connection" goes away.
        print("\n" + "=" * 70, flush=True)
        print("WAITING FOR CHROME EXTENSION TO RECONNECT", flush=True)
        print("In Chrome Agent: click the BrowserMCP extension icon →", flush=True)
        print("  if it says 'Connect': click it now", flush=True)
        print("  if it says 'Disconnect': click Disconnect THEN Connect again", flush=True)
        print("(this probe will auto-detect the handshake within 30s)", flush=True)
        print("=" * 70 + "\n", flush=True)

        connected = False
        t_start = time.time()
        for poll_id in range(50, 50 + 30):  # 30 attempts ~ 30s
            send(proc, {"jsonrpc": "2.0", "id": poll_id, "method": "tools/call",
                        "params": {"name": "browser_snapshot", "arguments": {}}})
            resp = recv(proc)
            text = resp.get("result", {}).get("content", [{}])[0].get("text", "")
            if "No connection to browser extension" in text or "No tab is connected" in text:
                time.sleep(1)
                continue
            # Got something non-error-y; assume connected
            log("handshake_complete", dt_s=round(time.time() - t_start, 1),
                snapshot_bytes=len(text), head=text[:200])
            connected = True
            break
        if not connected:
            log("handshake_timeout", dt_s=round(time.time() - t_start, 1))
            print("\nTIMED OUT waiting for extension handshake. Bailing.", flush=True)
            return

        # 4. Walk S1 then S2 — navigate + snapshot for each
        for stage_id, url in FIXTURES.items():
            log("stage_begin", stage=stage_id, url=url)
            t = time.time()
            nav = call_tool(proc, 200, "browser_navigate", {"url": url})
            nav_text = nav.get("result", {}).get("content", [{}])[0].get("text", "")[:500]
            log("navigate_result", stage=stage_id, dt_s=round(time.time() - t, 2),
                is_error=nav.get("result", {}).get("isError", False), text_head=nav_text)
            time.sleep(1.5)  # let DOM settle

            t = time.time()
            snap = call_tool(proc, 201, "browser_snapshot")
            snap_text = snap.get("result", {}).get("content", [{}])[0].get("text", "")
            log("snapshot_result", stage=stage_id, dt_s=round(time.time() - t, 2),
                bytes=len(snap_text), text_head=snap_text[:400])

        # 5. TLS fingerprint capture — navigate to Scrapfly, snapshot, parse JSON body
        log("tls_probe_begin", url=TLS_PROBE_URL)
        t = time.time()
        tls_nav = call_tool(proc, 300, "browser_navigate", {"url": TLS_PROBE_URL})
        log("tls_navigate", dt_s=round(time.time() - t, 2),
            text_head=tls_nav.get("result", {}).get("content", [{}])[0].get("text", "")[:300])
        time.sleep(3)
        tls_snap = call_tool(proc, 301, "browser_snapshot")
        tls_text = tls_snap.get("result", {}).get("content", [{}])[0].get("text", "")
        log("tls_snapshot", bytes=len(tls_text), full_text=tls_text[:2000])

        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    finally:
        try:
            stderr_log.close()
        except Exception:
            pass
        print("\n\n=== EVENTS_JSON_BEGIN ===")
        print(json.dumps(events, indent=2, default=str))
        print("=== EVENTS_JSON_END ===")

if __name__ == "__main__":
    main()

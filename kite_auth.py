#!/usr/bin/env python3
"""
kite_auth.py  —  Run ONCE every morning before market open
=============================================================
What it does:
  1. Opens the Kite login URL in your browser
  2. Starts a local server on port 8888 to catch the redirect
  3. Extracts the request_token automatically
  4. Exchanges it for an access_token
  5. Saves the access_token to kite_token.txt

Usage:
  python3 kite_auth.py

After running, the access_token is valid until midnight IST.
"""

import http.server
import threading
import webbrowser
import urllib.parse
import json
import os
from datetime import datetime
from kiteconnect import KiteConnect

# ── Credentials ────────────────────────────────────────────────────────────────
API_KEY    = "wtz1fcddvpom8p8y"
API_SECRET = "4g8i6c5gkuwokhgv1c9jxxioya2cz32l"
TOKEN_FILE = os.path.join(os.path.dirname(__file__), "kite_token.txt")

# ── Local redirect server ──────────────────────────────────────────────────────
_request_token = None

class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global _request_token
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        if "request_token" in params:
            _request_token = params["request_token"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            html = (
                "<html><body style='font-family:monospace;background:#0d1117;color:#3fb950;"
                "display:flex;align-items:center;justify-content:center;height:100vh;margin:0;'>"
                "<div style='text-align:center;'>"
                "<div style='font-size:3rem;'>&#10003;</div>"
                "<div style='font-size:1.5rem;margin-top:10px;'>Login successful!</div>"
                "<div style='color:#8b949e;margin-top:8px;'>You can close this tab.</div>"
                "</div></body></html>"
            )
            self.wfile.write(html.encode('utf-8'))
        else:
            self.send_response(400)
            self.end_headers()
    def log_message(self, *_): pass  # suppress logs


def get_access_token() -> str:
    """Full auth flow — opens browser, waits for token, returns access_token."""
    global _request_token
    _request_token = None

    kite = KiteConnect(api_key=API_KEY)
    login_url = kite.login_url()

    # Start local redirect server
    server = http.server.HTTPServer(("127.0.0.1", 8888), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    print("\n" + "─"*50)
    print("  NSE Stock Analyser — Kite Login")
    print("─"*50)
    print(f"  Opening Zerodha login in your browser...")
    print(f"  If it doesn't open, visit:\n  {login_url}\n")
    webbrowser.open(login_url)

    # Wait for redirect
    print("  Waiting for login... (complete login in the browser)")
    import time
    for _ in range(120):   # wait up to 2 minutes
        if _request_token:
            break
        time.sleep(1)
    server.shutdown()

    if not _request_token:
        raise TimeoutError("Login timed out after 2 minutes. Run kite_auth.py again.")

    # Exchange for access_token
    data = kite.generate_session(_request_token, api_secret=API_SECRET)
    access_token = data["access_token"]

    # Save to file with timestamp
    with open(TOKEN_FILE, "w") as f:
        json.dump({
            "access_token": access_token,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "user_id": data.get("user_id", "HY3239"),
        }, f)

    print(f"\n  ✅  Login successful!")
    print(f"  User: {data.get('user_name', '')} ({data.get('user_id', '')})")
    print(f"  Token saved to kite_token.txt")
    print(f"  Valid until midnight IST today\n")
    return access_token


def load_token() -> str:
    """Load today's token from file, or re-auth if stale/missing."""
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE) as f:
            data = json.load(f)
        today = datetime.now().strftime("%Y-%m-%d")
        if data.get("date") == today:
            return data["access_token"]
    # Token missing or from a different day — re-authenticate
    return get_access_token()


if __name__ == "__main__":
    token = get_access_token()
    print(f"  Access token: {token[:8]}...{token[-4:]}")

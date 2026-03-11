#!/usr/bin/env python3
"""
Live Stock Chart Server
Run: python3 run.py
Then open: http://localhost:8000
"""
import http.server, urllib.request, urllib.parse, json, os, sys

PORT = 8000

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=os.path.dirname(os.path.abspath(__file__)), **kw)

    def log_message(self, fmt, *args):
        # Suppress noisy access logs, only show errors
        if args and str(args[1]) not in ('200','304'):
            print(f"  {args[0]} {args[1]}", file=sys.stderr)

    def do_GET(self):
        # ── Proxy endpoint: /api/chart?sym=CL=F ────────────────────────────
        if self.path.startswith('/api/chart'):
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            sym    = params.get('sym', ['CL=F'])[0]
            sym_enc = urllib.parse.quote(sym, safe='')

            urls = [
                f"https://query1.finance.yahoo.com/v8/finance/chart/{sym_enc}?range=1d&interval=1m&includePrePost=false",
                f"https://query2.finance.yahoo.com/v8/finance/chart/{sym_enc}?range=1d&interval=1m&includePrePost=false",
            ]

            last_err = None
            for url in urls:
                try:
                    req = urllib.request.Request(url, headers={
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                        'Accept': 'application/json',
                    })
                    with urllib.request.urlopen(req, timeout=8) as resp:
                        data = resp.read()
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(data)
                    return
                except Exception as e:
                    last_err = str(e)
                    continue

            # All endpoints failed
            err = json.dumps({'error': last_err}).encode()
            self.send_response(502)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(err)
            return

        # ── Serve static files (HTML, JS, CSS) ─────────────────────────────
        super().do_GET()

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print(f"\n  ✅  Live Chart Server running")
    print(f"  👉  Open this in Chrome:  http://localhost:{PORT}\n")
    try:
        with http.server.HTTPServer(('', PORT), Handler) as s:
            s.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped.")

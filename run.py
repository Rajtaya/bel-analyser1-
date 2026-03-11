#!/usr/bin/env python3
"""
run.py  v11  —  Live chart server with Kite WebSocket feed
===========================================================
Modes:
  1. Kite (default): python3 run.py
  2. Yahoo fallback: python3 run.py --yahoo
  3. Streamlit mode: python3 run.py 8001
"""
import http.server, urllib.request, urllib.parse, json, os, sys, time

PORT     = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 8000
USE_KITE = "--yahoo" not in sys.argv

_kite_ready = False
_feed       = None

if USE_KITE:
    try:
        from kite_auth import load_token
        from kite_feed import (start as kite_start, get_candles,
                                get_last_price, INSTRUMENTS, TOKEN_BY_SYMBOL)
        token = load_token()
        _feed = kite_start(token)
        time.sleep(2)
        _kite_ready = True
        print(f"  ✅  Kite feed active — {len(INSTRUMENTS)} instruments")
    except Exception as e:
        print(f"  ⚠️  Kite feed unavailable ({e}) — using Yahoo Finance")
        _kite_ready = False

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=os.path.dirname(os.path.abspath(__file__)), **kw)

    def log_message(self, fmt, *args):
        if args and str(args[1]) not in ('200', '304'):
            print(f"  {args[0]} {args[1]}", file=sys.stderr)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if parsed.path == '/api/chart' and _kite_ready:
            sym   = params.get('sym', ['BEL'])[0].upper()
            token = TOKEN_BY_SYMBOL.get(sym)
            if token is None:
                try: token = int(sym)
                except ValueError: pass
            if token is None:
                self._yahoo(sym + '.NS'); return
            candles = get_candles(token)
            if not candles:
                self._yahoo(sym + '.NS'); return
            self._ok({"source":"kite","symbol":sym,"token":token,
                      "candles":candles,"last_price":get_last_price(token)})
            return

        if parsed.path == '/api/chart':
            sym = params.get('sym', ['CL=F'])[0]
            yf  = sym + '.NS' if not (sym.endswith('=F') or sym.startswith('^')) else sym
            self._yahoo(yf); return

        if parsed.path == '/api/status':
            from kite_feed import LAST_PRICE
            self._ok({"kite_active":_kite_ready,
                      "ticks":len(LAST_PRICE) if _kite_ready else 0}); return

        if parsed.path == '/api/watchlist':
            if _kite_ready:
                self._ok([{"token":t,"symbol":s} for t,s in INSTRUMENTS.items()])
            else:
                self._ok([]); return

        super().do_GET()

    def _ok(self, data):
        b = json.dumps(data).encode()
        self.send_response(200)
        self.send_header('Content-Type','application/json')
        self.send_header('Access-Control-Allow-Origin','*')
        self.end_headers(); self.wfile.write(b)

    def _err(self, code, msg):
        b = json.dumps({"error":msg}).encode()
        self.send_response(code)
        self.send_header('Content-Type','application/json')
        self.send_header('Access-Control-Allow-Origin','*')
        self.end_headers(); self.wfile.write(b)

    def _yahoo(self, sym):
        sym_enc = urllib.parse.quote(sym, safe='')
        for host in ['query1','query2']:
            url = f"https://{host}.finance.yahoo.com/v8/finance/chart/{sym_enc}?range=1d&interval=1m&includePrePost=false"
            try:
                req = urllib.request.Request(url, headers={
                    'User-Agent':'Mozilla/5.0','Accept':'application/json'})
                with urllib.request.urlopen(req, timeout=8) as r:
                    data = r.read()
                self.send_response(200)
                self.send_header('Content-Type','application/json')
                self.send_header('Access-Control-Allow-Origin','*')
                self.end_headers(); self.wfile.write(data); return
            except Exception as e:
                last = str(e)
        self._err(502, last)

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    if PORT == 8000:
        mode = "Kite WebSocket" if _kite_ready else "Yahoo Finance"
        print(f"\n  ✅  Live Chart Server ({mode})")
        print(f"  👉  http://localhost:{PORT}\n")
    try:
        with http.server.HTTPServer(('', PORT), Handler) as s:
            s.serve_forever()
    except KeyboardInterrupt:
        if _feed: _feed.stop()
        print("\n  Stopped.")

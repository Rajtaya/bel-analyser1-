#!/usr/bin/env python3
"""
kite_feed.py  —  Zerodha Kite WebSocket tick receiver
======================================================
Subscribes to live ticks for all watchlist instruments.
Builds 1-min OHLCV candles in memory.
Exposes get_candles(token) for run.py to serve via HTTP.

Architecture:
  KiteTicker (WebSocket) → on_ticks() → _build_candle()
                                       → CANDLE_STORE[token]
  run.py calls get_candles(token) → returns JSON for live_chart.html
"""

import threading
import time
from datetime import datetime, timezone
from collections import defaultdict
from kiteconnect import KiteTicker
from kite_auth import API_KEY, load_token

# ── Instrument tokens for your watchlist ────────────────────────────────────────
INSTRUMENTS = {
    # NSE Equities
    2714625:  "BEL",
    2513665:  "HAL",
    633601:   "ONGC",
    1207553:  "GAIL",
    3397121:  "IGL",
    3400961:  "MGL",
    6191617:  "ATGL",
    3771393:  "GUJGASLTD",
    2683393:  "GSPL",
    2953217:  "TCS",
    408065:   "INFY",
    969473:   "WIPRO",
    341249:   "HDFCBANK",
    895745:   "TATASTEEL",
    738561:   "RELIANCE",
}

TOKEN_BY_SYMBOL = {v: k for k, v in INSTRUMENTS.items()}

# ── In-memory candle store ─────────────────────────────────────────────────────
# Structure: CANDLE_STORE[instrument_token] = [
#   {"time": unix_ts, "open": x, "high": x, "low": x, "close": x, "volume": x}, ...
# ]
CANDLE_STORE  = defaultdict(list)
_current_bar  = {}   # instrument_token → current open bar
_store_lock   = threading.Lock()

# Latest tick price per token (for live price badge)
LAST_PRICE    = {}   # token → float
LAST_TICK_TIME = {}  # token → datetime


def _minute_ts(dt: datetime) -> int:
    """Floor a datetime to its minute boundary as a Unix timestamp."""
    floored = dt.replace(second=0, microsecond=0)
    return int(floored.timestamp())


def _build_candle(token: int, ltp: float, volume: int, tick_time: datetime):
    """Update or create the current 1-min candle for this token."""
    bar_ts = _minute_ts(tick_time)

    with _store_lock:
        LAST_PRICE[token]     = ltp
        LAST_TICK_TIME[token] = tick_time

        if token not in _current_bar or _current_bar[token]["time"] != bar_ts:
            # New minute — close previous bar and start a new one
            if token in _current_bar:
                CANDLE_STORE[token].append(dict(_current_bar[token]))
                # Keep only last 390 candles (full trading day = 375 mins)
                if len(CANDLE_STORE[token]) > 390:
                    CANDLE_STORE[token] = CANDLE_STORE[token][-390:]

            _current_bar[token] = {
                "time":   bar_ts,
                "open":   ltp,
                "high":   ltp,
                "low":    ltp,
                "close":  ltp,
                "volume": volume,
            }
        else:
            # Update existing bar
            bar = _current_bar[token]
            bar["high"]   = max(bar["high"], ltp)
            bar["low"]    = min(bar["low"],  ltp)
            bar["close"]  = ltp
            bar["volume"] += volume


def get_candles(token: int) -> list:
    """Return all completed candles + current open bar for this token."""
    with _store_lock:
        candles = list(CANDLE_STORE.get(token, []))
        if token in _current_bar:
            candles = candles + [dict(_current_bar[token])]
    return candles


def get_last_price(token: int) -> float | None:
    return LAST_PRICE.get(token)


# ── KiteTicker callbacks ───────────────────────────────────────────────────────
_kws = None

def on_ticks(ws, ticks):
    for tick in ticks:
        token  = tick["instrument_token"]
        ltp    = tick.get("last_price", 0)
        volume = tick.get("volume_traded", 0) or tick.get("last_quantity", 0) or 0
        ts     = tick.get("exchange_timestamp") or datetime.now(timezone.utc)
        if not isinstance(ts, datetime):
            ts = datetime.now(timezone.utc)
        if ltp and ltp > 0:
            _build_candle(token, ltp, volume, ts)


def on_connect(ws, response):
    tokens = list(INSTRUMENTS.keys())
    ws.subscribe(tokens)
    ws.set_mode(ws.MODE_FULL, tokens)
    print(f"  ✅  Kite WebSocket connected — subscribed to {len(tokens)} instruments")


def on_close(ws, code, reason):
    print(f"  ⚠️  WebSocket closed: {code} — {reason}")


def on_error(ws, code, reason):
    print(f"  ❌  WebSocket error: {code} — {reason}")


def on_reconnect(ws, attempts_count):
    print(f"  🔄  Reconnecting... attempt {attempts_count}")


def on_noreconnect(ws):
    print("  ❌  WebSocket gave up reconnecting. Restart the app.")


# ── Start feed ─────────────────────────────────────────────────────────────────
def start(access_token: str):
    """Start the KiteTicker in a background thread."""
    global _kws
    _kws = KiteTicker(API_KEY, access_token)
    _kws.on_ticks      = on_ticks
    _kws.on_connect    = on_connect
    _kws.on_close      = on_close
    _kws.on_error      = on_error
    _kws.on_reconnect  = on_reconnect
    _kws.on_noreconnect = on_noreconnect

    t = threading.Thread(target=_kws.connect, kwargs={"threaded": True}, daemon=True)
    t.start()
    print("  📡  Kite feed starting...")
    time.sleep(2)   # give it a moment to connect
    return _kws


def stop():
    if _kws:
        _kws.stop()


if __name__ == "__main__":
    # Quick test — prints ticks to console
    token = load_token()
    start(token)
    print("  Streaming ticks... Press Ctrl+C to stop\n")
    try:
        while True:
            time.sleep(5)
            for tk, sym in INSTRUMENTS.items():
                p = LAST_PRICE.get(tk)
                if p:
                    n = len(get_candles(tk))
                    print(f"  {sym:<14} ₹{p:>10,.2f}   candles={n}")
    except KeyboardInterrupt:
        stop()
        print("\n  Stopped.")

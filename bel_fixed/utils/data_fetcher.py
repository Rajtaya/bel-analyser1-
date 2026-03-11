"""
data_fetcher.py  ·  v9
-----------------------
Fetches OHLCV + info from Yahoo Finance.

Improvements vs v4:
  - certifi SSL fix applied at module load (fixes macOS cert errors)
  - yfinance ≥ 1.2.0 required (old 0.x had broken cookie/crumb auth)
  - Rate-limit protection: 1.5 s minimum between requests
  - Retry with exponential back-off on HTTP 429
  - Live price via fast_info.last_price patches the latest OHLCV row
  - get_live_price() exposed for per-second tick updates
  - Robust MultiIndex flattening
"""

import os
import ssl
import time
import certifi
import yfinance as yf
import pandas as pd
from typing import Optional, Tuple

# ── SSL fix (macOS) ────────────────────────────────────────────────────────────
os.environ.setdefault("SSL_CERT_FILE",  certifi.where())
os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
ssl._create_default_https_context = ssl.create_default_context  # noqa: SLF001

NSE_SUFFIX = ".NS"

TIMEFRAMES = {
    "1 Month":  {"period": "1mo",  "interval": "1d"},
    "6 Months": {"period": "6mo",  "interval": "1d"},
    "1 Year":   {"period": "1y",   "interval": "1d"},
    "2 Years":  {"period": "2y",   "interval": "1wk"},
    "5 Years":  {"period": "5y",   "interval": "1wk"},
}

# Commodity / futures / index tickers — no .NS suffix needed
COMMODITY_TICKERS = {
    "NG=F",   # Natural Gas NYMEX
    "CL=F",   # Crude Oil WTI
    "BZ=F",   # Brent Crude
    "GC=F",   # Gold
    "SI=F",   # Silver
    "HG=F",   # Copper
    "ZW=F",   # Wheat
    "ZC=F",   # Corn
    "^NSEI",  # Nifty 50
    "^BSESN", # Sensex
}

# ── Rate limiter ───────────────────────────────────────────────────────────────
_last_request_time: float = 0.0
_MIN_DELAY_SECONDS: float = 1.5

def _rate_limit() -> None:
    global _last_request_time
    elapsed = time.time() - _last_request_time
    wait    = _MIN_DELAY_SECONDS - elapsed
    if wait > 0:
        time.sleep(wait)
    _last_request_time = time.time()


def is_commodity(code: str) -> bool:
    c = code.strip().upper()
    return (c in COMMODITY_TICKERS or c.endswith("=F")
            or c.startswith("^") or ("." in c and not c.endswith(".NS")))


def get_ticker_symbol(stock_code: str) -> str:
    code = stock_code.strip().upper()
    return code if is_commodity(code) else code + NSE_SUFFIX


def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Flatten MultiIndex columns that yfinance sometimes returns."""
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] if isinstance(col, tuple) else col
                      for col in df.columns]
    rename_map = {c: c.title() for c in df.columns if c.lower() in
                  {"open", "high", "low", "close", "volume", "adj close"}}
    return df.rename(columns=rename_map)


def fetch_stock_data(
    stock_code: str,
    period: str = "1y",
    interval: str = "1d",
) -> Optional[pd.DataFrame]:
    """
    Return a clean OHLCV DataFrame with the latest row patched with
    the real-time price. Returns None on failure.
    """
    ticker = get_ticker_symbol(stock_code)
    wait_times = [2, 5, 10]

    for attempt, wait in enumerate(wait_times, 1):
        try:
            _rate_limit()
            raw = yf.download(
                ticker, period=period, interval=interval,
                progress=False, auto_adjust=True,
            )
            if raw is None or raw.empty:
                return None

            df = _flatten_columns(raw.copy())

            if "Volume" not in df.columns:
                df["Volume"] = 0

            needed = ["Open", "High", "Low", "Close", "Volume"]
            if any(c not in df.columns for c in needed):
                return None

            df = df[needed].copy()
            df = df.dropna(subset=["Open", "High", "Low", "Close"])
            df.index = pd.to_datetime(df.index).tz_localize(None)
            df.index.name = "Date"
            df["Volume"] = (pd.to_numeric(df["Volume"], errors="coerce")
                            .fillna(0).astype("int64"))
            df = df.sort_index()

            # Patch last row with live price
            live = get_live_price(stock_code)
            if live is not None and live > 0:
                last_idx = df.index[-1]
                df.loc[last_idx, "Close"] = live
                df.loc[last_idx, "High"]  = max(df.loc[last_idx, "High"], live)
                df.loc[last_idx, "Low"]   = min(df.loc[last_idx, "Low"],  live)

            return df

        except Exception as exc:
            msg = str(exc)
            if "429" in msg and attempt < len(wait_times):
                time.sleep(wait)
                continue
            print(f"[data_fetcher] {ticker} attempt {attempt}: {exc}")
            if attempt == len(wait_times):
                return None

    return None


def get_live_price(stock_code: str) -> Optional[float]:
    """Fetch real-time price using fast_info (low latency, low rate-limit risk)."""
    ticker_sym = get_ticker_symbol(stock_code)
    try:
        fi = yf.Ticker(ticker_sym).fast_info
        price = fi.last_price
        return float(price) if price and price > 0 else None
    except Exception:
        return None


def fetch_stock_info(stock_code: str) -> dict:
    ticker = get_ticker_symbol(stock_code)
    try:
        _rate_limit()
        info = yf.Ticker(ticker).info
        return info if isinstance(info, dict) else {}
    except Exception:
        return {}

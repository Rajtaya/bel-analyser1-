"""
indicators.py
-------------
Pure pandas / numpy technical indicators.
No dependency on the `ta` library — avoids install failures on macOS ARM.

All functions are safe on short DataFrames (< indicator window rows):
they return NaN-filled columns rather than raising exceptions.
"""

import pandas as pd
import numpy as np


# ── Helpers ──────────────────────────────────────────────────────────────────

def _safe_series(df: pd.DataFrame, col: str) -> pd.Series:
    """Return column as float64 Series, or empty Series if missing."""
    if col not in df.columns:
        return pd.Series(dtype=float)
    return df[col].astype(float)


# ── Moving Averages ───────────────────────────────────────────────────────────

def add_moving_averages(df: pd.DataFrame) -> pd.DataFrame:
    """SMA-50, SMA-200, EMA-20."""
    close = _safe_series(df, "Close")
    df = df.copy()
    df["SMA_50"]  = close.rolling(window=50,  min_periods=1).mean()
    df["SMA_200"] = close.rolling(window=200, min_periods=1).mean()
    df["EMA_20"]  = close.ewm(span=20, adjust=False, min_periods=1).mean()
    return df


# ── RSI ───────────────────────────────────────────────────────────────────────

def add_rsi(df: pd.DataFrame, window: int = 14) -> pd.DataFrame:
    """
    Wilder-smoothed RSI.
    Uses EWM with com=window-1, which matches the standard Wilder formula.
    """
    close = _safe_series(df, "Close")
    df = df.copy()
    delta = close.diff()
    gain  = delta.clip(lower=0)
    loss  = (-delta).clip(lower=0)
    avg_gain = gain.ewm(com=window - 1, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(com=window - 1, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["RSI"] = 100.0 - (100.0 / (1.0 + rs))
    return df


# ── MACD ──────────────────────────────────────────────────────────────────────

def add_macd(df: pd.DataFrame,
             fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """Standard MACD line, signal line, and histogram."""
    close = _safe_series(df, "Close")
    df = df.copy()
    ema_fast = close.ewm(span=fast,   adjust=False, min_periods=fast).mean()
    ema_slow = close.ewm(span=slow,   adjust=False, min_periods=slow).mean()
    macd     = ema_fast - ema_slow
    sig      = macd.ewm(span=signal,  adjust=False, min_periods=signal).mean()
    df["MACD"]        = macd
    df["MACD_Signal"] = sig
    df["MACD_Hist"]   = macd - sig
    return df


# ── Bollinger Bands ───────────────────────────────────────────────────────────

def add_bollinger_bands(df: pd.DataFrame,
                        window: int = 20, num_std: float = 2.0) -> pd.DataFrame:
    """
    Bollinger Bands: upper, middle (SMA), lower.
    BB_%B = (Close − Lower) / (Upper − Lower)  — position within bands.
    """
    close = _safe_series(df, "Close")
    df = df.copy()
    mid   = close.rolling(window=window, min_periods=1).mean()
    sigma = close.rolling(window=window, min_periods=1).std(ddof=0)
    upper = mid + num_std * sigma
    lower = mid - num_std * sigma
    band_width = (upper - lower).replace(0, np.nan)
    df["BB_Upper"]  = upper
    df["BB_Middle"] = mid
    df["BB_Lower"]  = lower
    df["BB_PctB"]   = (close - lower) / band_width
    return df


# ── Volume ────────────────────────────────────────────────────────────────────

def add_volume_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Volume SMA-20 and spike flag (> 1.5× average)."""
    df = df.copy()
    vol = df["Volume"].astype(float)
    vol_sma = vol.rolling(window=20, min_periods=1).mean()
    df["Volume_SMA20"] = vol_sma
    df["Volume_Spike"] = vol > (vol_sma * 1.5)
    return df


# ── ATR ───────────────────────────────────────────────────────────────────────

def add_atr(df: pd.DataFrame, window: int = 14) -> pd.DataFrame:
    """
    Average True Range via Wilder smoothing.
    TR = max(H−L, |H−Prev_Close|, |L−Prev_Close|)
    """
    df = df.copy()
    high  = _safe_series(df, "High")
    low   = _safe_series(df, "Low")
    close = _safe_series(df, "Close")
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low  - prev_close).abs(),
    ], axis=1).max(axis=1)
    df["ATR"] = tr.ewm(com=window - 1, min_periods=window, adjust=False).mean()
    return df


# ── Pipeline ──────────────────────────────────────────────────────────────────

def compute_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the full indicator pipeline in one call."""
    df = add_moving_averages(df)
    df = add_rsi(df)
    df = add_macd(df)
    df = add_bollinger_bands(df)
    df = add_volume_indicators(df)
    df = add_atr(df)
    return df

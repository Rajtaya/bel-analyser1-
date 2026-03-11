"""
analysis.py
-----------
Rule-based AI analysis engine.

All functions guard against:
  - Empty DataFrames
  - NaN in indicator columns  (short timeframes = few data points)
  - Missing columns           (indicators not computed yet)
"""

import pandas as pd
import numpy as np
from typing import Tuple, List


# ── Trend Detection ───────────────────────────────────────────────────────────

def detect_trend(df: pd.DataFrame) -> str:
    """
    Five-level trend classification using MA positioning, RSI, and MACD.
    Returns: "STRONG BULLISH" | "BULLISH" | "NEUTRAL" | "BEARISH" | "STRONG BEARISH"
    """
    if df is None or df.empty:
        return "NEUTRAL"

    last = df.iloc[-1]

    def _val(col, default=0.0):
        v = last.get(col, default)
        return default if pd.isna(v) else float(v)

    price    = _val("Close")
    sma50    = _val("SMA_50",  price)
    sma200   = _val("SMA_200", price)
    rsi      = _val("RSI",     50)
    macd     = _val("MACD",    0)
    macd_sig = _val("MACD_Signal", 0)

    score = 0

    # Price vs moving averages
    if price > sma50:   score += 1
    else:               score -= 1
    if price > sma200:  score += 1
    else:               score -= 1

    # Golden / death cross
    if sma50 > sma200:  score += 1
    else:               score -= 1

    # RSI momentum
    if rsi > 55:        score += 1
    elif rsi < 45:      score -= 1

    # MACD direction
    if macd > macd_sig: score += 1
    else:               score -= 1

    if   score >=  4: return "STRONG BULLISH"
    elif score >=  2: return "BULLISH"
    elif score <= -4: return "STRONG BEARISH"
    elif score <= -2: return "BEARISH"
    else:             return "NEUTRAL"


# ── Support & Resistance ──────────────────────────────────────────────────────

def find_support_resistance(
    df: pd.DataFrame,
    n_levels: int = 3,
    window: int = 10,
) -> Tuple[List[float], List[float]]:
    """
    Detect local pivot highs (resistance) and pivot lows (support).
    Returns (support_levels, resistance_levels) — each a sorted list.
    """
    if df is None or len(df) < window * 2 + 1:
        return [], []

    highs = df["High"].values.astype(float)
    lows  = df["Low"].values.astype(float)
    n     = len(df)

    res_idx = []
    sup_idx = []

    for i in range(window, n - window):
        segment_h = highs[i - window: i + window + 1]
        segment_l = lows[i  - window: i + window + 1]
        if not np.isnan(highs[i]) and highs[i] == np.nanmax(segment_h):
            res_idx.append(i)
        if not np.isnan(lows[i])  and lows[i]  == np.nanmin(segment_l):
            sup_idx.append(i)

    current = float(df["Close"].iloc[-1])

    def cluster(indices, prices):
        if not indices:
            return []
        raw = sorted([prices[i] for i in indices])
        grouped = [raw[0]]
        for p in raw[1:]:
            # Merge pivots within 1.5% of each other
            if abs(p - grouped[-1]) / max(grouped[-1], 1e-9) > 0.015:
                grouped.append(p)
        return sorted(grouped, key=lambda x: abs(x - current))[:n_levels]

    supports    = cluster(sup_idx,  lows)
    resistances = cluster(res_idx,  highs)
    return sorted(supports), sorted(resistances)


# ── Trading Signal ────────────────────────────────────────────────────────────

def generate_signal(df: pd.DataFrame) -> dict:
    """
    Composite BUY / HOLD / SELL signal with confidence (0–100) and reasons.
    """
    if df is None or df.empty:
        return {"signal": "HOLD", "confidence": 0, "reasons": ["No data available"]}

    last    = df.iloc[-1]
    reasons: List[str] = []
    score   = 0

    def _v(col, default=0.0):
        v = last.get(col, default)
        return default if pd.isna(v) else float(v)

    rsi      = _v("RSI",          50)
    macd     = _v("MACD",          0)
    macd_sig = _v("MACD_Signal",   0)
    macd_h   = _v("MACD_Hist",     0)
    price    = _v("Close")
    sma50    = _v("SMA_50",    price)
    sma200   = _v("SMA_200",   price)
    pctb     = _v("BB_PctB",     0.5)
    spike    = bool(last.get("Volume_Spike", False))

    # RSI
    if rsi < 30:
        score += 2
        reasons.append(f"RSI oversold ({rsi:.1f}) — buying opportunity")
    elif rsi > 70:
        score -= 2
        reasons.append(f"RSI overbought ({rsi:.1f}) — caution advised")
    else:
        reasons.append(f"RSI neutral ({rsi:.1f})")

    # MACD crossover
    if macd > macd_sig and macd_h > 0:
        score += 2
        reasons.append("MACD bullish crossover — upward momentum")
    elif macd < macd_sig and macd_h < 0:
        score -= 2
        reasons.append("MACD bearish crossover — downward momentum")
    else:
        reasons.append("MACD near crossover — watch closely")

    # Moving averages
    if price > sma50 > sma200:
        score += 2
        reasons.append("Price above SMA-50 & SMA-200 — confirmed uptrend")
    elif price < sma50 < sma200:
        score -= 2
        reasons.append("Price below SMA-50 & SMA-200 — confirmed downtrend")
    elif price > sma50:
        score += 1
        reasons.append("Price above SMA-50 — short-term bullish")
    else:
        score -= 1
        reasons.append("Price below SMA-50 — short-term bearish")

    # Bollinger Bands
    if pctb < 0.05:
        score += 1
        reasons.append("Near lower Bollinger Band — potential mean reversion")
    elif pctb > 0.95:
        score -= 1
        reasons.append("Near upper Bollinger Band — potential reversal")

    # Volume confirmation
    if spike and score > 0:
        score += 1
        reasons.append("High volume confirms bullish move")
    elif spike and score < 0:
        score -= 1
        reasons.append("High volume confirms bearish move")

    max_possible = 8
    confidence   = int(min(abs(score) / max_possible * 100, 100))

    if   score >=  3: signal = "BUY"
    elif score <= -3: signal = "SELL"
    else:             signal = "HOLD"

    return {"signal": signal, "confidence": confidence, "reasons": reasons}


# ── Risk Management ───────────────────────────────────────────────────────────

def calculate_risk_levels(df: pd.DataFrame) -> dict:
    """
    ATR-based stop-loss and target prices.
    Falls back to a 2% price-based stop if ATR is unavailable.
    """
    if df is None or df.empty:
        return {}

    last  = df.iloc[-1]
    price = float(last["Close"])

    atr_val = last.get("ATR", None)
    if atr_val is None or pd.isna(atr_val) or float(atr_val) == 0:
        atr = price * 0.02          # fallback: 2% of price
    else:
        atr = float(atr_val)

    stop_loss = round(price - 1.5 * atr, 2)
    stop_pct  = round((price - stop_loss) / price * 100, 2)
    risk_dist = price - stop_loss

    return {
        "current_price": round(price, 2),
        "stop_loss":     stop_loss,
        "stop_pct":      stop_pct,
        "target1":       round(price + 1.5 * risk_dist, 2),   # 1.5:1 R/R
        "target2":       round(price + 2.0 * risk_dist, 2),   # 2:1 R/R
        "target3":       round(price + 3.0 * risk_dist, 2),   # 3:1 R/R
        "atr":           round(atr, 2),
        "rr_ratio":      "2:1",
    }

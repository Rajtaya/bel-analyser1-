"""
metrics.py  ·  v9
------------------
Streamlit UI helper components.

Fixes vs v4:
  - All hardcoded ₹ symbols replaced with curr_sym parameter
  - render_risk_panel(risk, curr_sym) now accepts currency symbol
  - render_latest_indicators(df, curr_sym) passes currency through
  - _fmt() helper extended with curr_sym argument
  - All numeric formatting guarded against None / NaN
"""

import streamlit as st
import pandas as pd
import numpy as np


SIGNAL_STYLES = {
    "BUY":  {"bg": "#0d2818", "border": "#3fb950", "text": "#3fb950", "emoji": "🟢"},
    "SELL": {"bg": "#2d0e0e", "border": "#f85149", "text": "#f85149", "emoji": "🔴"},
    "HOLD": {"bg": "#1a1a0a", "border": "#e3b341", "text": "#e3b341", "emoji": "🟡"},
}

TREND_STYLES = {
    "STRONG BULLISH": {"color": "#3fb950", "emoji": "🚀"},
    "BULLISH":        {"color": "#56d364", "emoji": "📈"},
    "NEUTRAL":        {"color": "#e3b341", "emoji": "➡️"},
    "BEARISH":        {"color": "#f85149", "emoji": "📉"},
    "STRONG BEARISH": {"color": "#da3633", "emoji": "💥"},
}


def _fmt(value, fmt=",.2f", prefix="", suffix="") -> str:
    """Safely format a numeric value; return '—' on None/NaN."""
    if value is None:
        return "—"
    try:
        v = float(value)
        if np.isnan(v) or np.isinf(v):
            return "—"
        return f"{prefix}{v:{fmt}}{suffix}"
    except (TypeError, ValueError):
        return "—"


# ── Signal Card ───────────────────────────────────────────────────────────────

def render_signal_card(signal_data: dict) -> None:
    signal = signal_data.get("signal", "HOLD")
    conf   = signal_data.get("confidence", 0)
    s      = SIGNAL_STYLES.get(signal, SIGNAL_STYLES["HOLD"])

    st.markdown(f"""
    <div style="background:{s['bg']};border:2px solid {s['border']};
         border-radius:12px;padding:22px 20px;text-align:center;margin-bottom:10px;">
        <div style="font-size:2.6rem;line-height:1.1">{s['emoji']}</div>
        <div style="font-size:2rem;font-weight:800;color:{s['text']};
             letter-spacing:4px;font-family:monospace;margin:6px 0;">{signal}</div>
        <div style="color:#8b949e;font-size:0.85rem;">
            Confidence: <strong style="color:{s['text']}">{conf}%</strong>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ── Trend Badge ───────────────────────────────────────────────────────────────

def render_trend_badge(trend: str) -> None:
    s = TREND_STYLES.get(trend, TREND_STYLES["NEUTRAL"])
    st.markdown(f"""
    <div style="border-left:4px solid {s['color']};padding:10px 16px;
         background:rgba(255,255,255,0.03);border-radius:0 8px 8px 0;margin-bottom:12px;">
        <span style="font-size:1.3rem">{s['emoji']}</span>
        <span style="color:{s['color']};font-weight:700;font-family:monospace;
              font-size:1.1rem;margin-left:8px;">{trend}</span>
    </div>
    """, unsafe_allow_html=True)


# ── Risk Panel ────────────────────────────────────────────────────────────────

def render_risk_panel(risk: dict, curr_sym: str = "₹") -> None:
    """Render risk/reward table. curr_sym='$' for commodities, '₹' for NSE."""
    if not risk:
        st.info("Insufficient data for risk calculation.")
        return

    sym = curr_sym  # local alias for f-strings

    rows = [
        ("Current Price",
            _fmt(risk.get("current_price"), prefix=f"{sym} ", fmt=",.2f"), "#58a6ff"),
        ("ATR (14)",
            _fmt(risk.get("atr"),           prefix=f"{sym} ", fmt=",.2f"), "#e3b341"),
        (f"🛑 Stop Loss  (-{_fmt(risk.get('stop_pct'), fmt='.1f')}%)",
            _fmt(risk.get("stop_loss"),     prefix=f"{sym} ", fmt=",.2f"), "#f85149"),
        (f"🎯 Target 1  (1.5× R/R)",
            _fmt(risk.get("target1"),       prefix=f"{sym} ", fmt=",.2f"), "#56d364"),
        (f"🎯 Target 2  (2× R/R)",
            _fmt(risk.get("target2"),       prefix=f"{sym} ", fmt=",.2f"), "#3fb950"),
        (f"🎯 Target 3  (3× R/R)",
            _fmt(risk.get("target3"),       prefix=f"{sym} ", fmt=",.2f"), "#26a641"),
    ]

    table_rows = "".join(
        f"<tr><td style='color:#8b949e;font-size:0.84rem;padding:8px 12px;"
        f"border-bottom:1px solid #21262d;'>{label}</td>"
        f"<td style='text-align:right;font-weight:600;font-family:monospace;"
        f"color:{color};padding:8px 12px;border-bottom:1px solid #21262d;'>{value}</td></tr>"
        for label, value, color in rows
    )

    st.markdown(f"""
    <table style="width:100%;border-collapse:collapse;">
      {table_rows}
    </table>
    """, unsafe_allow_html=True)


# ── Signal Reasons ────────────────────────────────────────────────────────────

def render_signal_reasons(reasons: list) -> None:
    if not reasons:
        return
    items = "".join(
        f"<li style='margin:5px 0;color:#c9d1d9;font-size:0.88rem;line-height:1.5;'>• {r}</li>"
        for r in reasons
    )
    st.markdown(f"<ul style='padding-left:4px;margin:0;list-style:none;'>{items}</ul>",
                unsafe_allow_html=True)


# ── Indicator Snapshot Row ────────────────────────────────────────────────────

def render_latest_indicators(df: pd.DataFrame, curr_sym: str = "₹") -> None:
    """Six-column indicator snapshot — safe against NaN. Pass curr_sym='$' for commodities."""
    if df is None or df.empty:
        return

    last = df.iloc[-1]

    def _v(col, default=0.0):
        val = last.get(col, default)
        if val is None or (isinstance(val, float) and (np.isnan(val) or np.isinf(val))):
            return default
        return float(val)

    rsi_val = _v("RSI",       50)
    macd_h  = _v("MACD_Hist",  0)
    sma50   = _v("SMA_50",     0)
    sma200  = _v("SMA_200",    0)
    pctb    = _v("BB_PctB",    0.5)
    atr     = _v("ATR",        0)
    sym     = curr_sym

    rsi_col  = "#f85149" if rsi_val > 70 else "#3fb950" if rsi_val < 30 else "#e3b341"
    macd_col = "#3fb950" if macd_h >= 0 else "#f85149"

    items = [
        ("RSI (14)",  f"{rsi_val:.1f}",                     rsi_col),
        ("MACD Hist", f"{macd_h:.3f}",                      macd_col),
        ("SMA 50",    f"{sym}{sma50:,.2f}"  if sma50  else "—", "#58a6ff"),
        ("SMA 200",   f"{sym}{sma200:,.2f}" if sma200 else "—", "#d2a8ff"),
        ("BB %B",     f"{pctb:.2f}"         if pctb is not None else "—", "#ffa657"),
        ("ATR (14)",  f"{sym}{atr:,.2f}"    if atr    else "—", "#e3b341"),
    ]

    cols = st.columns(len(items))
    card = (
        "<div style='background:#161b22;border:1px solid #21262d;"
        "border-radius:8px;padding:10px 8px;text-align:center;'>"
        "<div style='color:#8b949e;font-size:0.72rem;margin-bottom:4px;'>{label}</div>"
        "<div style='color:{color};font-weight:700;font-family:monospace;"
        "font-size:0.95rem;'>{value}</div></div>"
    )
    for col, (label, value, color) in zip(cols, items):
        col.markdown(card.format(label=label, value=value, color=color),
                     unsafe_allow_html=True)

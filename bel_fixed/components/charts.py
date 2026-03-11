"""
charts.py  ·  v9
-----------------
All Plotly chart builders.  Mac / Windows / Linux compatible.

Fixes vs v4:
  - sr_chart now accepts curr_sym parameter — shows $ for commodities, ₹ for NSE
  - All hardcoded ₹ in annotation_text replaced with dynamic curr_sym
  - No deprecated layout params
  - Guards against all-NaN indicator columns
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ── Palette ───────────────────────────────────────────────────────────────────
C = {
    "bg":     "#0D1117",
    "paper":  "#161B22",
    "grid":   "#21262D",
    "text":   "#C9D1D9",
    "sub":    "#8B949E",
    "green":  "#3FB950",
    "red":    "#F85149",
    "blue":   "#58A6FF",
    "orange": "#FFA657",
    "purple": "#D2A8FF",
    "yellow": "#E3B341",
    "cyan":   "#39D353",
}


def _base_layout(title: str, height: int = 500) -> dict:
    return dict(
        title=dict(text=title, font=dict(color=C["text"], size=14, family="monospace")),
        paper_bgcolor=C["paper"],
        plot_bgcolor=C["bg"],
        font=dict(color=C["text"], family="monospace", size=11),
        height=height,
        margin=dict(l=10, r=60, t=50, b=20),
        hovermode="x unified",
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor=C["grid"],
            font=dict(color=C["sub"], size=10),
        ),
    )


def _xaxis_style(rangeslider: bool = False) -> dict:
    return dict(
        gridcolor=C["grid"],
        showgrid=True,
        zeroline=False,
        color=C["sub"],
        rangeslider=dict(visible=rangeslider),
    )


def _yaxis_style(side: str = "right") -> dict:
    return dict(
        gridcolor=C["grid"],
        showgrid=True,
        zeroline=False,
        color=C["sub"],
        side=side,
    )


# ─────────────────────────────────────────────────────────────────────────────
#  1. Candlestick + Overlays + Volume
# ─────────────────────────────────────────────────────────────────────────────

def candlestick_chart(df: pd.DataFrame, ticker: str) -> go.Figure:
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.75, 0.25],
        vertical_spacing=0.03,
        subplot_titles=["", ""],
    )

    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
        name="OHLC",
        increasing=dict(fillcolor=C["green"], line=dict(color=C["green"], width=1)),
        decreasing=dict(fillcolor=C["red"],   line=dict(color=C["red"],   width=1)),
    ), row=1, col=1)

    if "EMA_20" in df.columns and df["EMA_20"].notna().any():
        fig.add_trace(go.Scatter(
            x=df.index, y=df["EMA_20"], name="EMA 20",
            line=dict(color=C["orange"], width=1.2, dash="dot"),
        ), row=1, col=1)

    if "SMA_50" in df.columns and df["SMA_50"].notna().any():
        fig.add_trace(go.Scatter(
            x=df.index, y=df["SMA_50"], name="SMA 50",
            line=dict(color=C["blue"], width=1.5),
        ), row=1, col=1)

    if "SMA_200" in df.columns and df["SMA_200"].notna().any():
        fig.add_trace(go.Scatter(
            x=df.index, y=df["SMA_200"], name="SMA 200",
            line=dict(color=C["purple"], width=1.5),
        ), row=1, col=1)

    if "BB_Upper" in df.columns and df["BB_Upper"].notna().any():
        fig.add_trace(go.Scatter(
            x=df.index, y=df["BB_Upper"], name="BB Upper",
            line=dict(color=C["yellow"], width=1, dash="dash"),
            opacity=0.6,
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=df.index, y=df["BB_Lower"], name="BB Lower",
            line=dict(color=C["yellow"], width=1, dash="dash"),
            fill="tonexty", fillcolor="rgba(227,179,65,0.06)",
            opacity=0.6,
        ), row=1, col=1)

    vol_colors = [
        C["green"] if float(c) >= float(o) else C["red"]
        for c, o in zip(df["Close"], df["Open"])
    ]
    fig.add_trace(go.Bar(
        x=df.index, y=df["Volume"],
        name="Volume",
        marker=dict(color=vol_colors, opacity=0.7),
    ), row=2, col=1)

    if "Volume_SMA20" in df.columns and df["Volume_SMA20"].notna().any():
        fig.add_trace(go.Scatter(
            x=df.index, y=df["Volume_SMA20"], name="Vol SMA 20",
            line=dict(color=C["cyan"], width=1.5),
        ), row=2, col=1)

    layout = _base_layout(f"{ticker}  ·  Price & Volume", height=640)
    layout["xaxis"]  = _xaxis_style(rangeslider=False)
    layout["xaxis2"] = _xaxis_style(rangeslider=False)
    layout["yaxis"]  = _yaxis_style()
    layout["yaxis2"] = _yaxis_style()
    fig.update_layout(**layout)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
#  2. RSI
# ─────────────────────────────────────────────────────────────────────────────

def rsi_chart(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()

    fig.add_hrect(y0=70, y1=100, fillcolor=C["red"],   opacity=0.07, line_width=0)
    fig.add_hrect(y0=0,  y1=30,  fillcolor=C["green"], opacity=0.07, line_width=0)

    for level, color, label, pos in [
        (70, C["red"],   "Overbought (70)", "top left"),
        (50, C["sub"],   "",                "top left"),
        (30, C["green"], "Oversold (30)",   "bottom left"),
    ]:
        fig.add_hline(
            y=level,
            line_dash="dash" if level != 50 else "dot",
            line_color=color,
            line_width=1,
            annotation_text=label,
            annotation_position=pos,
            annotation_font_color=color,
        )

    fig.add_trace(go.Scatter(
        x=df.index, y=df["RSI"], name="RSI (14)",
        line=dict(color=C["cyan"], width=2),
        fill="tozeroy",
        fillcolor="rgba(57,211,83,0.06)",
    ))

    layout = _base_layout("RSI  ·  Relative Strength Index (14)", height=280)
    layout["xaxis"] = _xaxis_style()
    layout["yaxis"] = dict(**_yaxis_style(), range=[0, 100])
    fig.update_layout(**layout)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
#  3. MACD
# ─────────────────────────────────────────────────────────────────────────────

def macd_chart(df: pd.DataFrame) -> go.Figure:
    hist_vals   = df["MACD_Hist"].fillna(0)
    hist_colors = [C["green"] if v >= 0 else C["red"] for v in hist_vals]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df.index, y=hist_vals, name="Histogram",
        marker=dict(color=hist_colors, opacity=0.7),
    ))
    fig.add_trace(go.Scatter(
        x=df.index, y=df["MACD"], name="MACD",
        line=dict(color=C["blue"], width=2),
    ))
    fig.add_trace(go.Scatter(
        x=df.index, y=df["MACD_Signal"], name="Signal",
        line=dict(color=C["orange"], width=1.5, dash="dot"),
    ))
    fig.add_hline(y=0, line_color=C["sub"], line_width=0.8)

    layout = _base_layout("MACD  ·  (12, 26, 9)", height=280)
    layout["xaxis"] = _xaxis_style()
    layout["yaxis"] = _yaxis_style()
    fig.update_layout(**layout)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
#  4. Support & Resistance  — curr_sym param added
# ─────────────────────────────────────────────────────────────────────────────

def sr_chart(
    df: pd.DataFrame,
    supports: list,
    resistances: list,
    ticker: str,
    curr_sym: str = "₹",
) -> go.Figure:
    """Price line with S/R overlays. Pass curr_sym='$' for commodity futures."""
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df.index, y=df["Close"], name="Close",
        line=dict(color=C["blue"], width=1.8),
    ))

    for i, lvl in enumerate(supports, 1):
        fig.add_hline(
            y=lvl,
            line_dash="dash", line_color=C["green"], line_width=1.2,
            annotation_text=f"S{i}: {curr_sym}{lvl:,.2f}",
            annotation_position="top left",
            annotation_font_color=C["green"],
        )

    for i, lvl in enumerate(resistances, 1):
        fig.add_hline(
            y=lvl,
            line_dash="dash", line_color=C["red"], line_width=1.2,
            annotation_text=f"R{i}: {curr_sym}{lvl:,.2f}",
            annotation_position="top left",
            annotation_font_color=C["red"],
        )

    layout = _base_layout(f"{ticker}  ·  Support & Resistance", height=400)
    layout["xaxis"] = _xaxis_style()
    layout["yaxis"] = _yaxis_style()
    fig.update_layout(**layout)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
#  5. Trend / Price area chart
# ─────────────────────────────────────────────────────────────────────────────

def trend_chart(df: pd.DataFrame, ticker: str) -> go.Figure:
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df.index, y=df["Close"],
        name="Close Price",
        line=dict(color=C["blue"], width=2),
        fill="tozeroy",
        fillcolor="rgba(88,166,255,0.08)",
    ))

    if "SMA_50" in df.columns and df["SMA_50"].notna().any():
        fig.add_trace(go.Scatter(
            x=df.index, y=df["SMA_50"], name="SMA 50",
            line=dict(color=C["orange"], width=1.5, dash="dash"),
        ))

    layout = _base_layout(f"{ticker}  ·  Price Trend", height=340)
    layout["xaxis"] = _xaxis_style()
    layout["yaxis"] = _yaxis_style()
    fig.update_layout(**layout)
    return fig

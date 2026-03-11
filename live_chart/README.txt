╔══════════════════════════════════════════════════════════╗
║           LIVE COMMODITY & STOCK CHART                   ║
╚══════════════════════════════════════════════════════════╝

HOW TO RUN (takes 5 seconds)
─────────────────────────────
1. Open a Terminal

2. cd into this folder:
      cd ~/Downloads/live_chart

3. Start the server:
      python3 run.py

4. Open Chrome and go to:
      http://localhost:8000

5. To stop: press Ctrl+C in the terminal


WHY THE SERVER IS NEEDED
─────────────────────────
Browsers block direct fetch() calls to external sites
(Yahoo Finance) when opening a file:// HTML file — this
is called the "CORS policy". The Python server acts as a
local proxy: Chrome fetches from localhost (allowed), and
the server forwards the request to Yahoo Finance.


SYMBOLS AVAILABLE
──────────────────
  CL=F   Crude Oil WTI       (NYMEX)
  NG=F   Natural Gas         (NYMEX)
  BZ=F   Brent Crude         (ICE)
  GC=F   Gold                (COMEX)
  SI=F   Silver              (COMEX)
  BEL    BEL Ltd             (NSE India)
  ONGC   Oil & Natural Gas   (NSE India)
  GAIL   GAIL India          (NSE India)
  IGL    Indraprastha Gas    (NSE India)
  HAL    Hindustan Aeronaut. (NSE India)


FEATURES
─────────
  • 1-minute candlestick chart (full trading day)
  • Live price updates every second
  • New candles appear automatically
  • Green/red flash on price movement
  • Open, High, Low, Prev Close, Volume stats
  • Countdown bar showing next data refresh


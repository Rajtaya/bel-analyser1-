#!/usr/bin/env python3
"""
diagnose.py  — run ONCE before starting app to verify environment
Usage:  python3 diagnose.py
"""
import sys, importlib

REQUIRED = {
    "yfinance":  "1.2.0",
    "pandas":    "2.0.0",
    "numpy":     "1.26.0",
    "plotly":    "5.18.0",
    "streamlit": "1.32.0",
    "certifi":   "2024.0.0",
}

print("\n  NSE Stock Analyser — Dependency Check\n  " + "─"*40)
all_ok = True
for pkg, min_ver in REQUIRED.items():
    try:
        mod = importlib.import_module(pkg)
        ver = getattr(mod, "__version__", "?")
        print(f"  ✅  {pkg:<12} {ver}")
    except ImportError:
        print(f"  ❌  {pkg:<12} NOT INSTALLED  →  pip install {pkg}")
        all_ok = False

print()
# Test Yahoo Finance
print("  Testing Yahoo Finance connection…")
try:
    import yfinance as yf, certifi, os, ssl
    os.environ["SSL_CERT_FILE"] = certifi.where()
    ssl._create_default_https_context = ssl.create_default_context
    t  = yf.Ticker("BEL.NS")
    fi = t.fast_info
    p  = fi.last_price
    if p and p > 0:
        print(f"  ✅  BEL.NS live price: ₹{p:,.2f}")
    else:
        print("  ⚠️  BEL.NS returned no price (market may be closed)")
except Exception as e:
    print(f"  ❌  Yahoo Finance error: {e}")
    all_ok = False

print()
if all_ok:
    print("  ✅  All checks passed — run:  streamlit run app.py\n")
else:
    print("  ⚠️  Fix issues above, then run:  pip install -r requirements.txt\n")


# Step 1: Upgrade yfinance
pip install --upgrade yfinance

# Step 2: Test it works

import yfinance as yf
df = yf.Ticker('BEL.NS').history(period='5d')
print('✅ Live data working! Latest close:', df['Close'].iloc[-1])


# Step 3: Run app
streamlit run app.py

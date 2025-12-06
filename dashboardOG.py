import streamlit as st
import ccxt
import pandas as pd
import plotly.graph_objects as go
import time
import os
from datetime import datetime, timedelta

# -------------------------------------------
# 1. PAGE CONFIGURATION
# -------------------------------------------
st.set_page_config(page_title="🐋 Pro Crypto Dashboard", layout="wide")
st.title("⚡ Mission Control: Full History Analysis")

# -------------------------------------------
# 2. SIDEBAR & SETTINGS
# -------------------------------------------
with st.sidebar:
    st.header("⚙️ Data Settings")
    symbol = st.selectbox("Asset", ["BTC/USDT", "ETH/USDT", "SOL/USDT"])
    timeframe = st.selectbox("Timeframe", ["1d", "4h", "1h"])
    
    st.divider()
    st.header("📅 Time Travel")
    st.info("Select a specific date range to zoom in like TradingView.")
    
    # Default to "All Time" (None means no filter)
    use_date_filter = st.checkbox("Filter by Date Range", value=False)
    
    if use_date_filter:
        start_date = st.date_input("Start Date", value=datetime(2020, 1, 1))
        end_date = st.date_input("End Date", value=datetime(2020, 12, 31))
    else:
        start_date = None
        end_date = None
        
    st.divider()
    st.header("📐 Strategy Settings")
    bb_period = st.slider("Bollinger Period", 10, 50, 20)
    bb_std = st.slider("Std Dev", 1.0, 3.0, 2.0)

# -------------------------------------------
# 3. DATA ENGINE
# -------------------------------------------
@st.cache_data(ttl=3600) # Cache data for 1 hour to make it fast
def fetch_all_history(symbol, timeframe):
    filename = f"{symbol.replace('/', '_')}_{timeframe}.csv"
    exchange = ccxt.binance({'enableRateLimit': True})
    
    if os.path.exists(filename):
        df = pd.read_csv(filename)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    else:
        # Download data if file doesn't exist
        # Using a safer, smaller batch for immediate testing if file missing
        # For full history, this block runs once
        since = exchange.parse8601('2017-01-01T00:00:00Z')
        all_candles = []
        while True:
            candles = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=1000)
            if not candles: break
            all_candles += candles
            since = candles[-1][0] + 1
            if len(candles) < 1000: break
            time.sleep(0.1)
            
        df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.to_csv(filename, index=False)
        return df

def calculate_bands(df, period, std):
    df['middle'] = df['close'].rolling(window=period).mean()
    std_dev = df['close'].rolling(window=period).std()
    df['upper'] = df['middle'] + (std_dev * std)
    df['lower'] = df['middle'] - (std_dev * std)
    return df

# -------------------------------------------
# 4. MAIN DASHBOARD UI
# -------------------------------------------
# Load Data
try:
    with st.spinner('Loading History...'):
        df = fetch_all_history(symbol, timeframe)
        df = calculate_bands(df, bb_period, bb_std)

    # --- APPLY DATE FILTER ---
    if use_date_filter and start_date and end_date:
        # Filter the dataframe to only show the selected range
        mask = (df['timestamp'].dt.date >= start_date) & (df['timestamp'].dt.date <= end_date)
        df = df.loc[mask]

    last_row = df.iloc[-1]

    # --- METRICS ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Price", f"${last_row['close']:,.2f}")
    col2.metric("Date", f"{last_row['timestamp'].strftime('%Y-%m-%d')}")
    col3.metric("High (Selected)", f"${df['high'].max():,.2f}")
    col4.metric("Low (Selected)", f"${df['low'].min():,.2f}")

    # --- TRADINGVIEW STYLE CHART ---
    st.subheader(f"📜 {symbol} Chart")

    fig = go.Figure()

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df['timestamp'],
        open=df['open'], high=df['high'],
        low=df['low'], close=df['close'],
        name='Price'
    ))

    # Bands
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['upper'], line=dict(color='gray', width=1), name='Upper'))
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['lower'], line=dict(color='gray', width=1), name='Lower'))
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['middle'], line=dict(color='orange', width=1), name='Avg'))

    # Update Layout with Zoom Buttons
    fig.update_layout(
        height=700,
        template="plotly_dark",
        xaxis=dict(
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1m", step="month", stepmode="backward"),
                    dict(count=6, label="6m", step="month", stepmode="backward"),
                    dict(count=1, label="YTD", step="year", stepmode="todate"),
                    dict(count=1, label="1y", step="year", stepmode="backward"),
                    dict(step="all", label="All")
                ]),
                bgcolor="#2A2A2A" # Dark button background
            ),
            rangeslider=dict(visible=True), # Keep the bottom slider
            type="date"
        )
    )

    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Waiting for data... (If this is the first run, it might take 10 seconds). Error: {e}")
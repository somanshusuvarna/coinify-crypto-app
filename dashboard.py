import streamlit as st
import streamlit.components.v1 as components
import ccxt
import pandas as pd
import plotly.graph_objects as go
import time
import os
from datetime import datetime

# -------------------------------------------
# 1. PAGE CONFIGURATION
# -------------------------------------------
st.set_page_config(page_title="🐋 Pro Crypto Dashboard", layout="wide")
st.title("⚡ Mission Control Center")

# -------------------------------------------
# 2. SIDEBAR (Clean & Synchronized)
# -------------------------------------------
with st.sidebar:
    st.header("⚙️ Dashboard Settings")
    
    # This single selector controls BOTH charts
    selected_symbol = st.selectbox("Select Asset", ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"])
    
    st.info("✅ Signal Synchronized: Changing this asset updates both the Full History Analyzer and the Pro Terminal.")

# -------------------------------------------
# 3. ENGINE: PYTHON FULL HISTORY (Hidden Logic)
# -------------------------------------------
DEFAULT_TIMEFRAME = "1d"
BB_PERIOD = 20
BB_STD = 2.0

@st.cache_data(ttl=3600)
def fetch_history_cached(symbol, timeframe):
    filename = f"{symbol.replace('/', '_')}_{timeframe}.csv"
    exchange = ccxt.binance({'enableRateLimit': True})
    
    if os.path.exists(filename):
        df = pd.read_csv(filename)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    else:
        # First time download (Loops back to 2017)
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
# 4. DASHBOARD LAYOUT (Tabs)
# -------------------------------------------
tab1, tab2 = st.tabs(["📜 Full History Analysis", "📈 Pro Terminal (TradingView)"])

# === TAB 1: YOUR PYTHON ANALYZER ===
with tab1:
    st.subheader(f"{selected_symbol} // All-Time Performance")
    
    try:
        with st.spinner(f'Analyzing {selected_symbol} History...'):
            df = fetch_history_cached(selected_symbol, DEFAULT_TIMEFRAME)
            df = calculate_bands(df, BB_PERIOD, BB_STD)

        last_row = df.iloc[-1]
        
        # Metrics Row
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Current Price", f"${last_row['close']:,.2f}")
        c2.metric("All-Time High", f"${df['high'].max():,.2f}")
        c3.metric("All-Time Low", f"${df['low'].min():,.2f}")
        
        # Signal Logic
        if last_row['close'] < last_row['lower']:
            c4.metric("Bot Signal", "🟢 BUY ZONE", delta="Oversold")
        elif last_row['close'] > last_row['upper']:
            c4.metric("Bot Signal", "🔴 SELL ZONE", delta="Overbought", delta_color="inverse")
        else:
            c4.metric("Bot Signal", "💤 NEUTRAL", delta="Holding", delta_color="off")

        # Plotly Chart
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='Price'))
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['upper'], line=dict(color='gray', width=1), name='Upper'))
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['lower'], line=dict(color='gray', width=1), name='Lower'))
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['middle'], line=dict(color='orange', width=1), name='Avg'))
        
        fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=True, title=f"{selected_symbol} (2017 - Present)")
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Waiting for data... {e}")

# === TAB 2: TRADINGVIEW WIDGET ===
with tab2:
    st.subheader(f"{selected_symbol} // Professional Terminal")
    
    # Convert symbol for TradingView (e.g., "BTC/USDT" -> "BINANCE:BTCUSDT")
    tv_symbol = f"BINANCE:{selected_symbol.replace('/', '')}"

    # Embed Widget
    html_code = f"""
    <div class="tradingview-widget-container" style="height:100%;width:100%">
      <div class="tradingview-widget-container__widget" style="height:calc(100% - 32px);width:100%"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
      {{
      "width": "100%",
      "height": "800",
      "symbol": "{tv_symbol}",
      "interval": "D",
      "timezone": "Etc/UTC",
      "theme": "dark",
      "style": "1",
      "locale": "en",
      "enable_publishing": false,
      "allow_symbol_change": true,
      "calendar": false,
      "support_host": "https://www.tradingview.com"
    }}
      </script>
    </div>
    """
    
    # --- FIXED LINE BELOW ---
    components.html(html_code, height=800)
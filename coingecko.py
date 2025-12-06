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
st.set_page_config(page_title="🚀 Crypto Explorer", layout="wide", page_icon="🪙")

if 'selected_asset' not in st.session_state:
    st.session_state.selected_asset = None

# -------------------------------------------
# 2. DATA ENGINE
# -------------------------------------------
def get_market_data():
    """Fetches live data and sorts it for the UI."""
    exchange = ccxt.binance()
    symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT', 
               'DOGE/USDT', 'ADA/USDT', 'AVAX/USDT', 'DOT/USDT', 'MATIC/USDT']
    try:
        tickers = exchange.fetch_tickers(symbols)
        data = []
        for symbol, ticker in tickers.items():
            data.append({
                "Symbol": symbol,
                "Name": symbol.split('/')[0],
                "Price": ticker['last'],
                "Change": ticker['percentage'],
                "Volume": ticker['quoteVolume']
            })
        return pd.DataFrame(data)
    except:
        return pd.DataFrame()

# History logic (Same as before)
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
# 3. APP NAVIGATION
# -------------------------------------------

# === SCENE 1: THE "COINGECKO" HOME PAGE ===
if st.session_state.selected_asset is None:
    st.title("🪙 Crypto Market Tracker")
    st.markdown("Global cryptocurrency prices by 24h volume.")

    # 1. Fetch Data
    with st.spinner("Syncing with Binance..."):
        df = get_market_data()

    if not df.empty:
        # 2. Calculate "Highlights" (Trending Cards)
        top_gainer = df.loc[df['Change'].idxmax()]
        top_loser = df.loc[df['Change'].idxmin()]
        top_vol = df.loc[df['Volume'].idxmax()]

        # 3. Display Highlights Row
        st.subheader("🔥 Highlights")
        m1, m2, m3 = st.columns(3)
        
        with m1:
            st.container(border=True)
            st.metric("🚀 Top Gainer", f"{top_gainer['Name']}", f"+{top_gainer['Change']:.2f}%")
        
        with m2:
            st.container(border=True)
            st.metric("❄️ Top Loser", f"{top_loser['Name']}", f"{top_loser['Change']:.2f}%")
            
        with m3:
            st.container(border=True)
            st.metric("📊 High Volume", f"{top_vol['Name']}", f"${top_vol['Volume']/1000000:.1f}M")

        st.divider()

        # 4. The "CoinGecko" List
        st.subheader("Market Overview")
        
        # Header Row
        h1, h2, h3, h4, h5 = st.columns([1.5, 2, 2, 2, 1.5])
        h1.markdown("**Coin**")
        h2.markdown("**Price**")
        h3.markdown("**24h Change**")
        h4.markdown("**24h Volume**")
        h5.markdown("**Action**")
        
        # Data Rows
        for index, row in df.iterrows():
            c1, c2, c3, c4, c5 = st.columns([1.5, 2, 2, 2, 1.5])
            
            with c1:
                st.write(f"**{row['Name']}**")
            with c2:
                st.write(f"${row['Price']:,.2f}")
            with c3:
                val = row['Change']
                color = "green" if val > 0 else "red"
                symbol = "↑" if val > 0 else "↓"
                st.markdown(f":{color}[{symbol} {val:.2f}%]")
            with c4:
                st.write(f"${row['Volume']:,.0f}")
            with c5:
                # The Button
                if st.button(f"Analyze", key=f"btn_{row['Symbol']}"):
                    st.session_state.selected_asset = row['Symbol']
                    st.rerun()
            st.markdown("---") # Thin separator line

# === SCENE 2: MISSION CONTROL (Detailed View) ===
else:
    # Top Bar
    c_back, c_title = st.columns([1, 6])
    with c_back:
        if st.button("⬅️ Back"):
            st.session_state.selected_asset = None
            st.rerun()
    with c_title:
        st.header(f"{st.session_state.selected_asset} Analysis")

    asset = st.session_state.selected_asset
    
    # Tabs
    t1, t2 = st.tabs(["📜 Full History", "📈 Pro Terminal"])

    with t1:
        try:
            with st.spinner("Loading Chart..."):
                df = fetch_history_cached(asset, DEFAULT_TIMEFRAME)
                df = calculate_bands(df, BB_PERIOD, BB_STD)
            
            last = df.iloc[-1]
            # Metrics
            met1, met2, met3 = st.columns(3)
            met1.metric("Price", f"${last['close']:,.2f}")
            
            if last['close'] < last['lower']:
                met2.metric("Bot Signal", "BUY", "Oversold", delta_color="normal")
            elif last['close'] > last['upper']:
                met2.metric("Bot Signal", "SELL", "Overbought", delta_color="inverse")
            else:
                met2.metric("Bot Signal", "HOLD", "Neutral", delta_color="off")
                
            met3.metric("All-Time High", f"${df['high'].max():,.2f}")

            # Plotly Chart
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='Price'))
            fig.add_trace(go.Scatter(x=df['timestamp'], y=df['upper'], line=dict(color='gray', width=1), name='Upper'))
            fig.add_trace(go.Scatter(x=df['timestamp'], y=df['lower'], line=dict(color='gray', width=1), name='Lower'))
            fig.add_trace(go.Scatter(x=df['timestamp'], y=df['middle'], line=dict(color='orange', width=1), name='Avg'))
            fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=True, margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"Error: {e}")

    with t2:
        tv_symbol = f"BINANCE:{asset.replace('/', '')}"
        html_code = f"""
        <div class="tradingview-widget-container" style="height:100%;width:100%">
          <div class="tradingview-widget-container__widget" style="height:calc(100% - 32px);width:100%"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
          {{
          "width": "100%", "height": "800", "symbol": "{tv_symbol}", 
          "interval": "D", "timezone": "Etc/UTC", "theme": "dark", 
          "style": "1", "locale": "en", "enable_publishing": false, 
          "allow_symbol_change": true, "calendar": false, 
          "support_host": "https://www.tradingview.com"
        }}
          </script>
        </div>
        """
        components.html(html_code, height=800)
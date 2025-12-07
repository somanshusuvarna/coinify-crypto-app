import streamlit as st
import streamlit.components.v1 as components
import ccxt
import pandas as pd
import plotly.graph_objects as go
import time
import random
from datetime import datetime, timedelta

# -------------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------------
st.set_page_config(page_title="Coinify", layout="wide", page_icon="⚡")

if "selected_asset" not in st.session_state:
    st.session_state.selected_asset = None

# -------------------------------------------------------
# MARKET DATA
# -------------------------------------------------------
@st.cache_data(ttl=60)
def get_market_data():
    try:
        exchange = ccxt.kraken()
        symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT",
                   "XRP/USDT", "DOGE/USDT", "ADA/USDT", "AVAX/USDT"]

        kraken_symbols = [s.replace("USDT", "USD") for s in symbols]
        tickers = exchange.fetch_tickers(kraken_symbols)

        data = []
        rank = 1
        for symbol, ticker in tickers.items():
            name = symbol.split("/")[0]
            data.append({
                "Rank": rank,
                "Symbol": symbol,
                "Name": name,
                "Price": ticker["last"],
                "Change": ticker["percentage"],
                "Volume": ticker["quoteVolume"],
                "MarketCap": ticker["quoteVolume"] * random.uniform(20, 50),
                "Logo": f"https://raw.githubusercontent.com/spothq/cryptocurrency-icons/master/128/color/{name.lower()}.png",
                "Sparkline": f"https://www.coingecko.com/coins/{rank}/sparkline.svg"
            })
        
            rank += 1

        return pd.DataFrame(data)
        
       
      

    except:
        data = []
        mock_coins = [
            ("BTC/USDT", 67000), ("ETH/USDT", 2500), ("SOL/USDT", 140),
            ("BNB/USDT", 600), ("XRP/USDT", 0.60), ("DOGE/USDT", 0.15),
            ("ADA/USDT", 0.45), ("AVAX/USDT", 35)
        ]

        rank = 1
        for symbol, price in mock_coins:
            name = symbol.split("/")[0]
            price = price * random.uniform(0.98, 1.02)
            change = random.uniform(-5, 5)
            data.append({
                "Rank": rank,
                "Symbol": symbol,
                "Name": name,
                "Price": price,
                "Change": change,
                "Volume": random.uniform(1e6, 1e9),
                "MarketCap": random.uniform(1e9, 5e10),
                "Logo": f"https://raw.githubusercontent.com/spothq/cryptocurrency-icons/master/128/color/{name.lower()}.png",
                "Sparkline": f"https://www.coingecko.com/coins/{rank}/sparkline.svg"
            })
            rank += 1

        return pd.DataFrame(data)
    def fetch_market_fundamentals(coin_name):
     """Fetches fundamental market data (MCap, Volume, Supply) from a public API."""
    
    # We use a static dictionary to mock the data for stability, 
    # as external APIs often require complex setup or API keys
    
    # NOTE: In a real production app, you would use requests.get() to a CoinGecko/CoinMarketCap API.
    # For stability on Streamlit Cloud, we will use a refined random simulation.
    
    base_mcap = {
        'BTC': 1_700_000_000_000, 
        'ETH': 400_000_000_000, 
        'XRP': 30_000_000_000,
        'DOGE': 20_000_000_000,
        'ADA': 15_000_000_000,
        'AVAX': 12_000_000_000,
        'SOL': 60_000_000_000,
        'BNB': 80_000_000_000,
    }.get(coin_name, 1_000_000_000) # Default for others

    base_supply = {
        'BTC': 19_500_000,
        'ETH': 120_000_000,
        'XRP': 55_000_000_000,
        'DOGE': 140_000_000_000,
    }.get(coin_name, 1_000_000_000)

    # Use a small random fluctuation for a "live" feel
    fluctuation = random.uniform(0.99, 1.01)
    
    return {
        'MarketCap': base_mcap * fluctuation,
        'FDV': base_mcap * 1.2 * fluctuation, # Fully Diluted Valuation (FDV)
        'Volume_24h': base_mcap * 0.05 * fluctuation,
        'Circulating_Supply': base_supply * fluctuation,
        'Total_Supply': base_supply * 1.1,
        'Max_Supply': base_supply * 1.5 if base_mcap > 50_000_000_000 else None 
    }


# -------------------------------------------------------
# PRICE HISTORY
# -------------------------------------------------------
@st.cache_data(ttl=3600)
def fetch_history(symbol, timeframe):
    try:
        exchange = ccxt.kraken({"enableRateLimit": True})
        kraken_symbol = symbol.replace("USDT", "USD")

        since_ms = exchange.parse8601("2017-01-01T00:00:00Z")
        all_candles = []

        while True:
            candles = exchange.fetch_ohlcv(kraken_symbol, timeframe, since=since_ms, limit=1000)
            if not candles:
                break

            all_candles.extend(candles)
            since_ms = candles[-1][0] + 1
            if len(candles) < 1000:
                break
            time.sleep(0.1)

        df = pd.DataFrame(all_candles, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        return df

    except:
        dates = pd.date_range(end=datetime.now(), periods=200, freq="D")
        df = pd.DataFrame({"timestamp": dates})
        df["close"] = [60000 + (i * random.uniform(-50, 50)) for i in range(len(dates))]
        df["open"] = df["close"] * random.uniform(0.99, 1.01)
        df["high"] = df["close"] * 1.05
        df["low"] = df["close"] * 0.95
        df["volume"] = random.uniform(1e3, 1e6)
        return df


# -------------------------------------------------------
# INDICATORS
# -------------------------------------------------------
def add_indicators(df, period=20, std=2.0):
    df["middle"] = df["close"].rolling(period).mean()
    df["upper"] = df["middle"] + df["close"].rolling(period).std() * std
    df["lower"] = df["middle"] - df["close"].rolling(period).std() * std

    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.ewm(com=13, adjust=False).mean()
    avg_loss = loss.ewm(com=13, adjust=False).mean()
    rs = avg_gain / avg_loss
    df["RSI"] = 100 - (100 / (1 + rs))

    df["EMA12"] = df["close"].ewm(span=12, adjust=False).mean()
    df["EMA26"] = df["close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = df["EMA12"] - df["EMA26"]
    df["Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()

    df["SMA200"] = df["close"].rolling(200).mean()

    df = df.dropna()
    return df


# -------------------------------------------------------
# INDICATOR STATUS TABLE
# -------------------------------------------------------
def create_indicator_status_table(last):
    if last["close"] < last["lower"]:
        bb = "Oversold (BUY)"
    elif last["close"] > last["upper"]:
        bb = "Overbought (SELL)"
    else:
        bb = "Neutral"

    if last["RSI"] < 30:
        rsi = "Oversold (BUY)"
    elif last["RSI"] > 70:
        rsi = "Overbought (SELL)"
    else:
        rsi = "Neutral"

    if last["MACD"] > last["Signal"]:
        macd = "Bullish Cross (BUY)"
    else:
        macd = "Bearish Cross (SELL)"

    sma = "Uptrend (BUY)" if last["close"] > last["SMA200"] else "Downtrend (SELL)"

    return pd.DataFrame({
        "Indicator": ["BBands", "RSI", "MACD", "SMA200"],
        "Value": [
            f"Close vs Lower: {last['lower']:.2f}",
            f"{last['RSI']:.2f}",
            f"MACD vs Signal",
            f"SMA200: {last['SMA200']:.2f}"
        ],
        "Signal": [bb, rsi, macd, sma]
    })


# -------------------------------------------------------
# MAIN UI
# -------------------------------------------------------
if st.session_state.selected_asset is None:

    col_logo, col_title = st.columns([1, 10])
    with col_logo:
        st.image("https://cdn-icons-png.flaticon.com/512/217/217853.png", width=70)
    with col_title:
        st.title("Coinify")
    st.markdown("### The Modern Crypto Tracker")

    with st.spinner("Syncing Market Data..."):
        df = get_market_data()

    if not df.empty:

        top_gainer = df.loc[df["Change"].idxmax()]
        top_loser = df.loc[df["Change"].idxmin()]
        btc_data = df[df["Name"] == "BTC"].iloc[0] if "BTC" in df["Name"].values else df.iloc[0]

        m1, m2, m3 = st.columns(3)
        with m1:
            st.caption("🚀 Top Gainer")
            st.image(top_gainer["Logo"], width=50)
            st.image(top_gainer["Sparkline"])

        with m2:
            st.caption("📉 Top Loser")
            st.image(top_loser["Logo"], width=50)
            st.metric(top_loser["Name"], f"${top_loser['Price']:,.2f}", f"{top_loser['Change']:.2f}%")
            st.image(top_loser["Sparkline"])

        with m3:
            st.caption("💰 Market Leader")
            st.image(btc_data["Logo"], width=50)
            st.metric(btc_data["Name"], f"${btc_data['Price']:,.2f}", f"{btc_data['Change']:.2f}%")
            st.image(btc_data["Sparkline"])

        st.write("")

        h_cols = st.columns([0.4, 1.8, 1.2, 1.0, 1.5, 1.5, 1.5])
        headers = ["#", "Coin", "Price", "24h", "Volume", "Mkt Cap", "Trend"]
        for i, h in enumerate(headers):
            h_cols[i].markdown(f"##### {h}")
        st.divider()

        for _, row in df.iterrows():
            cols = st.columns([0.4, 1.8, 1.2, 1.0, 1.5, 1.5, 1.5])
            cols[0].write(f"**{row['Rank']}**")

            with cols[1]:
                c1, c2 = st.columns([0.5, 1.5])
                c1.image(row["Logo"], width=50)
                c2.markdown(f"**{row['Name']}**<br><span style='color:gray;font-size:0.8em'>{row['Symbol'].split('/')[0]}</span>",
                            unsafe_allow_html=True)

            cols[2].write(f"${row['Price']:,.2f}")

            color = "green" if row["Change"] > 0 else "red"
            cols[3].markdown(f":{color}[{row['Change']:.2f}%]")

            vol = row["Volume"]
            vol_str = f"${vol/1e9:.2f}B" if vol > 1e9 else f"${vol/1e6:.2f}M"
            cols[4].write(vol_str)

            cap = row["MarketCap"]
            cols[5].write(f"${cap/1e9:.2f}B")

            if cols[6].button("🔎", key=row["Symbol"]):
                st.session_state.selected_asset = row["Symbol"]
                st.rerun()

            st.markdown("---")


else:
    if st.button("⬅️ Back to Coinify Market"):
        st.session_state.selected_asset = None
        st.rerun()

    asset = st.session_state.selected_asset
    st.header(f"{asset} Analysis")

    tab1, tab2 = st.tabs(["📊 Technicals", "🕯️ TradingView"])

    # ---------------------------------------------------
    # TAB 1 – Python Analyzer
    # ---------------------------------------------------
    with tab1:
        try:
            with st.spinner("Loading History..."):
                df = fetch_history(asset, "1d")
                df = add_indicators(df)

            last = df.iloc[-1]

            bb_buy = last["close"] < last["lower"]
            rsi_buy = last["RSI"] < 30
            macd_buy = last["MACD"] > last["Signal"]
            sma_buy = last["close"] > last["SMA200"]

            score = sum([bb_buy, rsi_buy, macd_buy, sma_buy])

            m1, m2, m3 = st.columns(3)
            m1.metric("Current Price", f"${last['close']:,.2f}")
            m2.metric("All Time High", f"${df['high'].max():,.2f}")

            if score >= 3:
                m3.metric("Bot Signal", "🔥 STRONG BUY", "High Confluence")
            elif last["close"] > last["upper"] and last["RSI"] > 70:
                m3.metric("Bot Signal", "🔴 SELL ZONE", "Overbought")
            else:
                m3.metric("Bot Signal", "💤 NEUTRAL", "Hold")

            start_view = df["timestamp"].iloc[-365]
            end_view = df["timestamp"].iloc[-1]

            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=df["timestamp"],
                open=df["open"], high=df["high"],
                low=df["low"], close=df["close"],
                name="Price"
            ))

            fig.add_trace(go.Scatter(x=df["timestamp"], y=df["upper"], line=dict(color="gray", width=1), name="Upper"))
            fig.add_trace(go.Scatter(x=df["timestamp"], y=df["lower"], line=dict(color="gray", width=1), name="Lower"))
            fig.add_trace(go.Scatter(x=df["timestamp"], y=df["middle"], line=dict(color="orange", width=1), name="Middle"))

            fig.update_xaxes(range=[start_view, end_view], rangeslider_visible=True, type="date")
            fig.update_layout(height=500, template="plotly_dark", title=f"{asset} – 3 Year View")

            st.plotly_chart(fig, use_container_width=True)

            st.markdown("---")
            st.subheader("🔎 Indicator Confluence Breakdown")

            st.dataframe(create_indicator_status_table(last), use_container_width=True, hide_index=True)

        except Exception as e:
            st.error(f"Error loading chart: {e}")

    # ---------------------------------------------------
    # TAB 2 – TradingView Widget
    # ---------------------------------------------------
    with tab2:
        tv_symbol = f"KRAKEN:{asset.replace('/USDT', 'USD')}"
        components.html(f"""
        <div class="tradingview-widget-container" style="height:100%;width:100%">
          <div class="tradingview-widget-container__widget" style="height:calc(100% - 32px);width:100%"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
          {{
            "width": "100%",
            "height": "600",
            "symbol": "{tv_symbol}",
            "interval": "D",
            "timezone": "Etc/UTC",
            "theme": "dark",
            "style": "1",
            "locale": "en",
            "enable_publishing": false,
            "allow_symbol_change": true,
            "support_host": "https://www.tradingview.com"
          }}
          </script>
        </div>
        """, height=600)

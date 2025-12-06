import random
import datetime
import pandas as pd
import numpy as np
import ccxt

# -----------------------------
# 1. Configuration (The Ingredients)
# -----------------------------
config = {
    "mode": "backtest",
    "use_mock_data": False,
    "symbol": "BTC/USDT",
    "trade_amount": 100,
    "stop_loss_pct": 0.02,
    "take_profit_pct": 0.04,
    "ema_fast": 9,       # <--- The bot was missing this!
    "ema_slow": 21,      # <--- And this!
    "rsi_period": 14,
    "rsi_overbought": 70,
    "rsi_oversold": 30,
}

# -----------------------------
# 2. Data Helper
# -----------------------------
def get_historical_data(symbol, timeframe='1h', limit=300):
    try:
        exchange = ccxt.binance()
        bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(bars, columns=['timestamp','open','high','low','close','volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['close'] = df['close'].astype(float)
        return df
    except:
        print("⚠️ Binance connection failed. Using fake data for testing.")
        dates = pd.date_range(end=datetime.datetime.now(), periods=limit, freq='h')
        return pd.DataFrame({'timestamp': dates, 'close': [30000 + i*10 for i in range(limit)]})

# -----------------------------
# 3. Strategy Logic
# -----------------------------
def add_indicators(df, config):
    df['ema_fast'] = df['close'].ewm(span=config["ema_fast"]).mean()
    df['ema_slow'] = df['close'].ewm(span=config["ema_slow"]).mean()
    
    # RSI Calculation
    delta = df['close'].diff()
    gain = delta.clip(lower=0).fillna(0)
    loss = -delta.clip(upper=0).fillna(0)
    avg_gain = gain.rolling(window=config["rsi_period"]).mean()
    avg_loss = loss.rolling(window=config["rsi_period"]).mean()
    rs = avg_gain / (avg_loss + 1e-10)
    df['rsi'] = 100 - (100 / (1 + rs))
    return df

def generate_signal(row, config):
    if row['ema_fast'] > row['ema_slow'] and row['rsi'] < config["rsi_overbought"]:
        return "buy"
    elif row['ema_fast'] < row['ema_slow'] and row['rsi'] > config["rsi_oversold"]:
        return "sell"
    return "hold"

# -----------------------------
# 4. The Backtest Loop
# -----------------------------
def backtest(config):
    print("\n🚀 Starting backtest...")
    df = get_historical_data(config["symbol"], limit=500)
    df = add_indicators(df, config)

    balance = 1000
    position = None 
    entry_price = 0
    trades = []
    
    for i in range(1, len(df)):
        row = df.iloc[i]
        signal = generate_signal(row, config)

        if position is None and signal == "buy":
            position = 'long'
            entry_price = row['close']
            print(f"[{i}] 🟢 BUY  @ {row['close']:.2f}")

        elif position == 'long' and signal == "sell":
            profit = (row['close'] - entry_price) / entry_price
            balance += balance * profit
            outcome = "WIN" if profit > 0 else "LOSS"
            trades.append(outcome)
            print(f"[{i}] 🔴 SELL @ {row['close']:.2f} | P/L: {profit*100:.2f}% | Bal: ${balance:.0f}")
            position = None

    print(f"\n✅ Final Balance: ${balance:.2f}")

if __name__ == "__main__":
    backtest(config)
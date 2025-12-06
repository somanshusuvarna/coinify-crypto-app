import ccxt
import pandas as pd
import numpy as np
import itertools

# -----------------------------
# 1. Fetch Data Once (The Setup)
# -----------------------------
def get_data(symbol='BTC/USDT', limit=1000):
    print(f"⬇️ Fetching {limit} candles for {symbol}...")
    exchange = ccxt.binance()
    bars = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=limit)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

# -----------------------------
# 2. The Strategy Engine (Fast Version)
# -----------------------------
def run_backtest(df, params):
    # Unpack parameters we are testing
    fast_len = params['ema_fast']
    slow_len = params['ema_slow']
    rsi_len = params['rsi_period']
    rsi_buy = params['rsi_buy_threshold']  # e.g., 30
    rsi_sell = params['rsi_sell_threshold'] # e.g., 70
    
    # Calculate Indicators
    # (We use .copy() to avoid SettingWithCopy warnings on the main df)
    test_df = df.copy()
    test_df['ema_fast'] = test_df['close'].ewm(span=fast_len).mean()
    test_df['ema_slow'] = test_df['close'].ewm(span=slow_len).mean()
    
    # RSI Calc
    delta = test_df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=rsi_len).mean()
    avg_loss = loss.rolling(window=rsi_len).mean()
    rs = avg_gain / (avg_loss + 1e-10)
    test_df['rsi'] = 100 - (100 / (1 + rs))

    # Simulation Variables
    balance = 1000
    position = None
    entry_price = 0
    trades = 0
    wins = 0
    
    # Fast Loop (Vectorized logic is harder to read, so we keep your loop style for now)
    for i in range(slow_len, len(test_df)):
        row = test_df.iloc[i]
        price = row['close']
        
        # BUY Logic
        if position is None:
            if row['ema_fast'] > row['ema_slow'] and row['rsi'] < rsi_sell:
                position = 'long'
                entry_price = price
        
        # SELL Logic
        elif position == 'long':
            # Sell if cross down OR RSI is overheated (optional exit)
            if row['ema_fast'] < row['ema_slow']:
                profit = (price - entry_price) / entry_price
                balance = balance * (1 + profit)
                trades += 1
                if profit > 0: wins += 1
                position = None

    return {
        "balance": balance,
        "trades": trades,
        "win_rate": (wins/trades * 100) if trades > 0 else 0,
        "params": params
    }

# -----------------------------
# 3. The Grid Search (The "Brain")
# -----------------------------
def optimize():
    # 1. Get Data
    df = get_data(limit=2000) # <--- Increased to 2000 candles for better reliability
    
    # 2. Define Ranges to Test (WIDER RANGE)
    ema_fast_range = [10, 20, 50]
    ema_slow_range = [50, 100, 200] # <--- Added big trend lines
    rsi_buy_range = [30]     
    rsi_sell_range = [70, 75, 80]
    
    # Generate all combinations
    combinations = list(itertools.product(ema_fast_range, ema_slow_range, rsi_buy_range, rsi_sell_range))
    print(f"🧪 Testing {len(combinations)} different strategies on 2000 hours of data...")
    
    best_result = {"balance": 0}
    
    for combo in combinations:
        # SKIP invalid combos (e.g. Fast EMA 50 cannot be >= Slow EMA 50)
        if combo[0] >= combo[1]:
            continue
            
        params = {
            "ema_fast": combo[0],
            "ema_slow": combo[1],
            "rsi_period": 14,
            "rsi_buy_threshold": combo[2],
            "rsi_sell_threshold": combo[3]
        }
        
        # Run test
        result = run_backtest(df, params)
        
        # Print only PROFITABLE results
        if result['balance'] > 1000:
            print(f"✅ Found Profit: ${result['balance']:.2f} | Params: {params}")
            
        if result['balance'] > best_result['balance']:
            best_result = result

    print("\n🏆 BEST PARAMETERS FOUND:")
    print(f"Final Balance: ${best_result['balance']:.2f}")
    print(f"Win Rate: {best_result['win_rate']:.2f}%")
    print(f"Settings: {best_result['params']}")
    
if __name__ == "__main__":
    optimize()
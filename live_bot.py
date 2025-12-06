import ccxt
import pandas as pd
import time
import datetime

# -----------------------------
# 1. Configuration
# -----------------------------
config = {
    "symbol": "BTC/USDT",
    "timeframe": "1h",
    "limit": 100,
    "bb_period": 20,
    "bb_std_dev": 2.0,
    "check_interval": 3600, # Check every 3600 seconds (1 hour)
    "mode": "simulation",   # "simulation" = fake money, "live" = real money
}

# -----------------------------
# 2. Connect to Exchange (Binance)
# -----------------------------
# NOTE: For "simulation", we don't need real API keys yet.
exchange = ccxt.binance() 

def fetch_data(symbol, limit):
    try:
        bars = exchange.fetch_ohlcv(symbol, timeframe=config['timeframe'], limit=limit)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        return pd.DataFrame()

def get_signal(df):
    # Calculate Bollinger Bands
    df['middle_band'] = df['close'].rolling(window=config['bb_period']).mean()
    std_dev = df['close'].rolling(window=config['bb_period']).std()
    df['upper_band'] = df['middle_band'] + (std_dev * config['bb_std_dev'])
    df['lower_band'] = df['middle_band'] - (std_dev * config['bb_std_dev'])
    
    last_row = df.iloc[-1]
    price = last_row['close']
    
    # Logic: "Rubber Band" Strategy
    if price < last_row['lower_band']:
        return "buy", price, last_row['lower_band']
    elif price > last_row['middle_band']:
        return "sell", price, last_row['middle_band']
    else:
        return "hold", price, last_row['middle_band']

# -----------------------------
# 3. The "Forever" Loop
# -----------------------------
def run_bot():
    print(f"🤖 Live Bot Started in [{config['mode']}] mode...")
    print(f"🌊 Strategy: Bollinger Bands Reversion")
    print("Press Ctrl+C to stop.\n")

    while True:
        try:
            # 1. Get Data
            print(f"⏳ Checking market at {datetime.datetime.now().strftime('%H:%M:%S')}...")
            df = fetch_data(config['symbol'], config['limit'])
            
            if not df.empty:
                # 2. Analyze
                signal, price, band_level = get_signal(df)
                
                # 3. Act
                if signal == "buy":
                    print(f"🟢 BUY SIGNAL! Price ${price:.2f} is below lower band ${band_level:.2f}")
                    # If config['mode'] == 'live': exchange.create_market_buy_order(...)
                    
                elif signal == "sell":
                    print(f"🔴 SELL SIGNAL! Price ${price:.2f} reverted to mean ${band_level:.2f}")
                    # If config['mode'] == 'live': exchange.create_market_sell_order(...)
                    
                else:
                    print(f"💤 Holding. Price ${price:.2f} is inside bands.")
            
            # 4. Wait for the next check
            print(f"Sleeping for {config['check_interval']} seconds...\n")
            time.sleep(config['check_interval'])
            
        except KeyboardInterrupt:
            print("\n🛑 Bot stopped by user.")
            break
        except Exception as e:
            print(f"⚠️ Unexpected Error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    run_bot()
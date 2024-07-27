import pandas as pd
import okx.MarketData as MarketData
import os
import time
import requests
from dotenv import load_dotenv
from telegram import Bot
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

api_key = os.getenv('OKX_API_KEY')
secret_key = os.getenv('OKX_SECRET')
passphrase = os.getenv('OKX_PASS')
telegram_token = os.getenv('TELEGRAM_TOKEN')
telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
flag = "1"  # live trading: 0, demo trading: 1


def send_telegram_message(message):
    bot = Bot(token=telegram_token)
    bot.send_message(chat_id=telegram_chat_id, text=message)
def is_red_candle(candle):
    return candle['close'] < candle['open']

def is_green_candle(candle):
    return candle['close'] > candle['open']

def is_bearish_three_line_strike(windows):
    if len(windows) != 4:
        return False
    
    first_candle = windows.iloc[0]
    second_candle = windows.iloc[1]
    third_candle = windows.iloc[2]
    fourth_candle = windows.iloc[3]
    
    # First candle conditions
    first_candle_condition = (
        is_red_candle(first_candle)  # Red candle
    )
    print("first_candle_condition",first_candle_condition)

    # Second candle conditions
    second_candle_condition = (
        is_red_candle(second_candle) and  # Red candle
        first_candle['open'] > second_candle['open'] > first_candle['close'] and  # the opening price is within the previous body
        second_candle['close'] < first_candle['close']  # the closing price is below the previous closing price
    )
    print("second_candle_condition",second_candle_condition)

    # Third candle conditions
    third_candle_condition = (
        is_red_candle(third_candle) and  # Red candle
        second_candle['open'] > third_candle['open'] > second_candle['close'] and  # the opening price is within the previous body
        third_candle['close'] < second_candle['close']  # the closing price is below the previous closing price
    )
    print("third_candle_condition",third_candle_condition)

    # Fourth candle conditions
    fourth_candle_condition = (
        is_green_candle(fourth_candle) and  # Green candle
        fourth_candle['close'] >= first_candle['open']  # candle’s body engulfs all previous red bodies
    )
    print("fourth_candle_condition",fourth_candle_condition)
    
    # Check for Bearish Three Line Strike pattern
    if (first_candle_condition and second_candle_condition and
        third_candle_condition and fourth_candle_condition):
        return True
    else:
        return False

def backtest_strategy(df):
    signals = []
    for i in range(4, len(df)+1):
        window = df.iloc[i-4:i]  # 4 candles
        print(window)
        if is_bearish_three_line_strike(window):
            signals.append(window.iloc[-1]['timestamp'])  # Record pattern signal
    
    return signals


def get_candlestick_data(symbol, bar_size, limit):
    market_data_api = MarketData.MarketAPI(api_key, secret_key, passphrase, False, flag)

    data = market_data_api.get_history_candlesticks(instId=symbol, bar=bar_size, limit=limit)
    if data['code'] == '0':  # '0' as a string to match the format in the response
        # Adjust columns based on actual data structure
        df = pd.DataFrame(data['data'], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'quote_volume', 'timeframe_volume', 'count'])
        df[['open', 'high', 'low', 'close', 'volume', 'quote_volume', 'timeframe_volume', 'count']] = df[['open', 'high', 'low', 'close', 'volume', 'quote_volume', 'timeframe_volume', 'count']].astype(float)
        return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]  # Select relevant columns
    else:
        print("Error retrieving data:", data['msg'])
        return pd.DataFrame()

def main():
    # df = get_candlestick_data("BTC-USDT", "15m", 100)  # Assuming df is obtained from get_candlestick_data()
    # df.to_csv(csv_filename, index=False) 
        
    csv_filename = "candlestick_data.csv"
    df_from_csv = pd.read_csv(csv_filename)
    print(len(df_from_csv))
    signals = backtest_strategy(df_from_csv)
    if signals:
        print("Bearish Three-Line Strike pattern:")
        for signal in signals:
            readable_time = datetime.fromtimestamp(signal / 1000.0)
            print(readable_time)
    else:
        print("No signals")

if __name__ == "__main__":
    main()

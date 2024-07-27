import pandas as pd
import os
import time
from datetime import datetime
import requests
from telegram import Bot
from dotenv import load_dotenv
import okx.MarketData as MarketData

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

def is_bearish_three_line_strike(window):
    if len(window) != 4:
        return False

    first_candle = window.iloc[0]
    second_candle = window.iloc[1]
    third_candle = window.iloc[2]
    fourth_candle = window.iloc[3]

    first_candle_condition = is_red_candle(first_candle)
    second_candle_condition = (is_red_candle(second_candle) and
                               first_candle['open'] > second_candle['open'] > first_candle['close'] and
                               second_candle['close'] < first_candle['close'])
    third_candle_condition = (is_red_candle(third_candle) and
                              second_candle['open'] > third_candle['open'] > second_candle['close'] and
                              third_candle['close'] < second_candle['close'])
    fourth_candle_condition = (is_green_candle(fourth_candle) and
                               fourth_candle['close'] >= first_candle['open'])

    return (first_candle_condition and second_candle_condition and
            third_candle_condition and fourth_candle_condition)

def get_candlestick_data(symbol, bar_size, limit):
    market_data_api = MarketData.MarketAPI(api_key, secret_key, passphrase, False, flag)
    data = market_data_api.get_history_candlesticks(instId=symbol, bar=bar_size, limit=limit)
    if data['code'] == '0':
        df = pd.DataFrame(data['data'], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'quote_volume', 'timeframe_volume', 'count'])
        df[['open', 'high', 'low', 'close', 'volume', 'quote_volume', 'timeframe_volume', 'count']] = df[['open', 'high', 'low', 'close', 'volume', 'quote_volume', 'timeframe_volume', 'count']].astype(float)
        return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].iloc[::-1]  # Reverse to get the correct order
    else:
        print("Error retrieving data:", data['msg'])
        return pd.DataFrame()

def main():
    symbol = "BTC-USDT"
    bar_size = "15m"
    limit = 100

    while True:
        df = get_candlestick_data(symbol, bar_size, limit)
        if not df.empty:
            signals = []
            for i in range(4, len(df) + 1):
                window = df.iloc[i - 4:i]
                if is_bearish_three_line_strike(window):
                    signals.append(window.iloc[-1]['timestamp'])

            if signals:
                for signal in signals:
                    readable_time = datetime.fromtimestamp(signal / 1000.0)
                    message = f"Bearish Three-Line Strike pattern detected at {readable_time}"
                    send_telegram_message(message)
                    print(message)
            else:
                print("No signals detected.")
        
        # Wait for the next candlestick
        time.sleep(15 * 60)  # 15 minutes

if __name__ == "__main__":
    main()

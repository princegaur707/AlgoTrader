import requests
import pandas as pd
from io import StringIO
import yfinance as yf


def get_nifty_50_stocks():
    url_nifty = "https://archives.nseindia.com/content/indices/ind_nifty50list.csv"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
    }
    response_nifty = requests.get(url_nifty, headers=headers)
    response_nifty.raise_for_status()
    nifty_50_data = StringIO(response_nifty.text)
    df_nifty = pd.read_csv(nifty_50_data)

    url_tokens = 'https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json'
    response_tokens = requests.get(url_tokens)
    token_data = response_tokens.json()
    df_tokens = pd.DataFrame(token_data)

    nifty_50_symbols = df_nifty['Symbol'].tolist()
    df_filtered = df_tokens[(df_tokens['exch_seg'] == 'NSE') & (df_tokens['symbol'].str.contains('-EQ'))]
    df_nifty_50 = df_filtered[df_filtered['symbol'].str.replace('-EQ', '').isin(nifty_50_symbols)]

    return df_nifty_50[['symbol', 'token', 'name']]


def get_index_info():
    index_data = {
        '99926000': {'symbol': 'Nifty 50', 'name': 'NIFTY'},
        '99926009': {'symbol': 'Nifty Bank', 'name': 'BANKNIFTY'},
        '99926011': {'symbol': 'NIFTY MIDCAP 100', 'name': 'NIFTY MIDCAP'},
        '99919000': {'symbol': 'Sensex', 'name': 'SENSEX'}
    }
    return index_data


def get_nifty_200_stocks():
    url_nifty = "https://archives.nseindia.com/content/indices/ind_nifty200list.csv"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
    }
    response_nifty = requests.get(url_nifty, headers=headers)
    response_nifty.raise_for_status()
    nifty_200_data = StringIO(response_nifty.text)
    df_nifty = pd.read_csv(nifty_200_data)

    return df_nifty


def calculate_magic_number_for_tickers(nifty_200):
    nifty200_symbols = nifty_200['Symbol'].tolist()
    nifty200_tickers = [symbol + ".NS" for symbol in nifty200_symbols]

    hist = yf.download(nifty200_tickers, period="1mo", group_by='ticker')

    stock_data_list = []

    for ticker in nifty200_tickers:
        if ticker not in hist.columns or len(hist[ticker]['Volume']) < 21:
            print(f"Not enough data for {ticker}. Skipping...")
            continue

        ticker_data = hist[ticker]

        today_data = ticker_data.iloc[-1]

        open_price = today_data['Open']
        high_price = today_data['High']
        low_price = today_data['Low']
        close_price = today_data['Close']
        current_volume = today_data['Volume']

        volume_avg_20 = ticker_data['Volume'].iloc[-21:-1].mean()

        sma_20 = ticker_data['Close'].iloc[-21:-1].mean()

        prev_close = ticker_data['Close'].iloc[-2]  # The close of the previous day
        price_change_percent = ((close_price - prev_close) / prev_close) * 100

        # Calculate the magic number
        magic_number = (current_volume / volume_avg_20) * price_change_percent if volume_avg_20 != 0 else None

        # Append data for the ticker
        stock_data_list.append({
            "ticker": ticker,
            "open_price": open_price,
            "high_price": high_price,
            "low_price": low_price,
            "close_price": close_price,
            "current_volume": current_volume,
            "20_day_volume_avg": volume_avg_20,
            "20_day_sma": sma_20,
            "price_change_percent": price_change_percent,
            "magic_number": magic_number
        })

    sorted_data = sorted(stock_data_list, key=lambda x: x['magic_number'] if x['magic_number'] is not None else -float('inf'), reverse=True)
    top_gainers = sorted_data[:10]
    top_losers = sorted_data[-10:]

    return {
        "top_gainers": top_gainers,
        "top_losers": top_losers
    }

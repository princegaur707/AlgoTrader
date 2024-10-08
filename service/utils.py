import requests
import pandas as pd
from io import StringIO


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


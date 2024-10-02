from decimal import Decimal, InvalidOperation

import requests
from django.db import transaction
from django.http import JsonResponse
from django.views import View
from SmartApi import SmartConnect
import pyotp
import pandas as pd
from datetime import datetime, timedelta
import json
import yfinance as yf
import http.client
from django.conf import settings

from service.models import StockData, FinancialMetric, FinancialData

# Create an object of SmartConnect
apikey = settings.API_KEY
obj = SmartConnect(api_key=apikey)

def login():
    """
    Function to login and return AUTH and FEED tokens.
    """
    username = settings.USERNAME
    pwd = settings.PWD
    token = settings.TOKEN
    data = obj.generateSession(username, pwd, pyotp.TOTP(token).now())
    refreshToken = data['data']['refreshToken']
    auth_token = data['data']['jwtToken']
    feed_token = obj.getfeedToken()
    return auth_token, feed_token

def historical_data(exchange, token, from_date, to_date, timeperiod):
    """
    Function to fetch historical data and return it as a JSON string.
    """
    try:
        historicParam = {
            "exchange": exchange,
            "symboltoken": token,
            "interval": timeperiod,
            "fromdate": from_date, 
            "todate": to_date
        }
        api_response = obj.getCandleData(historicParam)
        data = api_response['data']
        columns = ['DateTime', 'Open', 'High', 'Low', 'Close', 'Volume']
        df = pd.DataFrame(data, columns=columns)
        
        # Convert DateTime to a datetime object and set it as index
        df['DateTime'] = pd.to_datetime(df['DateTime'])
        df.set_index('DateTime', inplace=True)

        # Convert DataFrame to JSON
        return df.reset_index().to_json(orient='records', date_format='iso')  # ISO format for date
    except Exception as e:
        print("Historic API failed: {}".format(e))
        return None  # Return None if there is an error
    
def market_data(token):
    """
    Function to fetch historical data and return it as a JSON string.
    """
    try:
        conn = http.client.HTTPSConnection("apiconnect.angelone.in")

        payload = {
            "mode": "FULL",
            "exchangeTokens": {
                "NSE": ['526', '694', '3351', '10940', '2885', '3506', '7229', '910', '1363', '1232', '11630', '20374', '157', '16675', '236', '5258', '10999', '25', '467', '1594', '3499', '11536', '2031', '16669', '2475', '547', '3045', '3787', '881', '13538', '4306', '5900', '1660', '17818', '317', '21808', '3456', '11723', '17963', '1394', '3432', '11532', '15083', '1922', '11483', '1348', '4963', '1333', '10604', '14977']
            }
        }

        json_payload = json.dumps(payload)

        headers = {
            'X-PrivateKey': apikey,  # Replace with your actual API key
            'Accept': 'application/json',
            'X-SourceID': 'WEB',
            'X-UserType': 'USER',
            'Authorization': f'{token}',  # Replace with your actual authorization token
            'Content-Type': 'application/json'
        }

        # Make the POST request
        conn.request("POST", "/rest/secure/angelbroking/market/v1/quote/", json_payload, headers)

        # Get the response
        res = conn.getresponse()
        data = res.read()

        # Print the response data
        

        # Close the connection
        conn.close()
        return(data.decode("utf-8"))
     
    except Exception as e:
        print("Market API failed: {}".format(e))
        return None  # Return None if there is an error


def get_nifty_200_stocks():
    url = "https://archives.nseindia.com/content/indices/ind_nifty200list.csv"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
    }

    try:
        # Fetch the CSV file from the URL
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Check that the request was successful

        # Read the content of the file into a pandas DataFrame
        from io import StringIO
        data = StringIO(response.text)
        df = pd.read_csv(data)

        return df

    except Exception as e:
        print("Failed to retrieve or parse the data:", e)
        return None

def fetch_quarterly_data(ticker):
    try:
        ticker = f"{ticker}.NS"
        stock = yf.Ticker(ticker)
        financials = stock.quarterly_financials
        market_cap = stock.info["marketCap"]
        data = {
        "Operating Income": financials.loc['Operating Income', :],
        "Total Revenue": financials.loc["Total Revenue", :],
        "Basic EPS":  financials.loc['Basic EPS', :],
        "Market Cap": market_cap
        }
        return data
    except Exception as err:
        print(err)

def fetch_annual_data(ticker):
    try:
        ticker = f"{ticker}.NS"
        stock = yf.Ticker(ticker)
        financials = stock.financials
        market_cap = stock.info["marketCap"]
        data = {
        "Operating Income": financials.loc['Operating Income', :],
        "Total Revenue": financials.loc["Total Revenue", :],
        "Basic EPS":  financials.loc['Basic EPS', :],
        "Market Cap": market_cap
        }
        return data
    except Exception as err:
        print(err)


class HistoricalDataView(View):
    def get(self, request):
        # Authenticate and get tokens
        auth_token, feed_token = login()

        # Calculate date range
        thirty_days_ago = datetime.now() - timedelta(days=900)
        from_date = thirty_days_ago.strftime("%Y-%m-%d %H:%M")
        to_date = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Get parameters from request
        exchange = request.GET.get('exchange', 'NSE')  # Default is NSE
        token = request.GET.get('token', 1333)         # Default is 1333
        timeperiod = request.GET.get('timeperiod', 'ONE_DAY')  # Default is ONE_MINUTE

        # Fetch historical data
        json_output = historical_data(exchange, token, from_date, to_date, timeperiod)

        if not json_output:
            return JsonResponse({'error': 'Failed to fetch historical data'}, status=500)

        # Parse JSON output
        data = json.loads(json_output)

        # Process data to get day-wise high, low, close, and calculate change %
        daily_data = {}
        for entry in data:
            date = entry['DateTime'].split('T')[0]  # Extract date
            open_price = entry['Open']
            high_price = entry['High']
            low_price = entry['Low']
            close_price = entry['Close']
            volume = entry['Volume']

            if date not in daily_data:
                daily_data[date] = {
                    'Date': date,
                    'Open': open_price,
                    'High': high_price,
                    'Low': low_price,
                    'Close': close_price,
                    'Volume': volume,
                    'PTD_Close': None,
                    'Change': None  # Initialize Change% to None
                }
            else:
                daily_data[date]['High'] = max(daily_data[date]['High'], high_price)
                daily_data[date]['Low'] = min(daily_data[date]['Low'], low_price)
                daily_data[date]['Close'] = close_price
                daily_data[date]['Volume'] += volume

        # Calculate PTD (Previous Day Close) and Change %
        previous_day_close = None
        for date in sorted(daily_data.keys()):
            if previous_day_close is not None:
                daily_data[date]['PTD_Close'] = previous_day_close
                
                # Calculate Change % and update the entry
                if previous_day_close > 0:  # Avoid division by zero
                    daily_data[date]['Change'] = ((daily_data[date]['Close'] - previous_day_close) / previous_day_close) * 100
                else:
                    daily_data[date]['Change'] = None  # or set to 0 if appropriate

            previous_day_close = daily_data[date]['Close']

        # Convert daily_data back to list
        result = list(daily_data.values())

        return JsonResponse(result, safe=False)

class MarketDataView(View):
     def get(self, request):
        # Authenticate and get tokens
        auth_token, feed_token = login()

       
        # Fetch historical data
        json_output = market_data(auth_token)

        if not json_output:
            return JsonResponse({'error': 'Failed to fetch historical data'}, status=500)

        # Parse JSON output
        data = json.loads(json_output)
        return JsonResponse(data, safe=False)

class FundamentalView(View):
    def get(self, request):
        ticker = request.GET.get('symbol')
        stock = yf.Ticker(ticker)
        
        # Fetch general info
        info = stock.info
        
        # Fetch financials (income statement)
        financials = stock.financials
        # Fetch balance sheet
        balance_sheet = stock.balance_sheet


        
        # Extract data and store in a dictionary
        stock_data = {}
        
        # Last Traded Price (LTP)
        stock_data['LTP'] = info.get('previousClose')
        
        # PE ratio
        stock_data['PE'] = info.get('trailingPE')  # Trailing PE
        
        # Debt to Equity ratio
        # total_debt = balance_sheet.loc['Total Debt'][0] if 'Total Debt' in balance_sheet.index else None
        # total_equity = balance_sheet.loc['Stockholders Equity'][0] if 'Stockholders Equity' in balance_sheet.index else None
        # stock_data['Debt to Equity'] = total_debt / total_equity if total_debt and total_equity else None
        stock_data['Debt to Equity']=info.get("debtToEquity")
        
        # Earnings Per Share (EPS)
        stock_data['EPS'] = info.get('trailingEps')  # Trailing EPS
        
        # Book Value Per Share (BVPS)
        stock_data['BVPS'] = info.get('bookValue')  # Book Value per share
        
        # Net Profit (most recent)
        net_income = financials.loc['Net Income'][0] if 'Net Income' in financials.index else None
        stock_data['Net Profit'] = net_income
        
        # Dividend Per Share (DPS)
        stock_data['DPS'] = info.get('dividendRate')  # DPS based on annual dividend
        
        # Net Profit Margin (NPM)
        total_revenue = financials.loc['Total Revenue'][0] if 'Total Revenue' in financials.index else None
        stock_data['NPM'] = (net_income / total_revenue) * 100 if net_income and total_revenue else None
        
        # Return on Equity (ROE)
        # stock_data['ROE'] = info.get('returnOnEquity') * 100 if info.get('returnOnEquity') else None
        
        return JsonResponse(stock_data, safe=False)

class StocksDataView(View):
    def get(self, request):
        df = get_nifty_200_stocks()
        if df is not None:
            for index, row in df.iterrows():
                stock, created = StockData.objects.update_or_create(
                    isin_code=row['ISIN Code'],
                    defaults={
                        'company_name': row['Company Name'],
                        'industry': row['Industry'],
                        'symbol': row['Symbol'],
                        'series': row['Series']
                    }
                )
            return JsonResponse({'message': 'Stock data imported successfully'}, status=200)
        else:
            return JsonResponse({'error': 'Failed to fetch stock data'}, status=500)



class FinancialDataView(View):
    def get(self, request, period='annual'):
        fetch_data = fetch_annual_data if period == 'annual' else fetch_quarterly_data
        stocks = StockData.objects.all()

        successful_updates = 0
        with transaction.atomic():
            for stock in stocks:
                print(f"stock: {stock}")
                data = fetch_data(stock.symbol)
                if data:
                    for metric_name, values in data.items():
                        metric, _ = FinancialMetric.objects.get_or_create(metric_name=metric_name)

                        if isinstance(values, pd.Series):

                            if period == 'annual':
                                limited_values = values.head(4)
                            else:
                                limited_values = values.head(5)

                            for date, value in limited_values.items():
                                try:
                                    date = pd.to_datetime(date).date()
                                    val = Decimal(value) if pd.notna(value) else None
                                    financial_data, created = FinancialData.objects.update_or_create(
                                        stock=stock,
                                        metric=metric,
                                        date=date,
                                        period=period,
                                        defaults={'value': val}
                                    )

                                    if created or (financial_data.value != val and pd.notna(value)):
                                        successful_updates += 1
                                except (InvalidOperation, TypeError):
                                    print(f"Error converting value {value} for metric {metric_name}")
                        else:
                            date = pd.to_datetime('today').date()
                            try:
                                value = Decimal(values)
                                financial_data, created = FinancialData.objects.update_or_create(
                                    stock=stock,
                                    metric=metric,
                                    date=date,
                                    period=period,
                                    defaults={'value': value}
                                )
                                if created or financial_data.value != value:
                                    successful_updates += 1
                            except (InvalidOperation, TypeError):
                                print(f"Error converting Market Cap value {values}")

        return JsonResponse({'message': f'Financial data for {period} period imported or updated successfully, total updates: {successful_updates}'}, status=200)
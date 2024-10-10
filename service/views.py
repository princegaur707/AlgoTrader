import time

from django.http import JsonResponse
from django.views import View
from SmartApi import SmartConnect
import pyotp
import pandas as pd
from datetime import datetime, timedelta
import json
import yfinance as yf
import http.client
from service.constants import *
from service.utils import get_nifty_50_stocks, get_nifty_200_stocks, calculate_magic_number_for_tickers

# Create an object of SmartConnect
apikey = API_KEY
obj = SmartConnect(api_key=API_KEY)
nifty_50_data = get_nifty_50_stocks()
nifty_200 = get_nifty_200_stocks()


def login():
    """
    Function to login and return AUTH and FEED tokens.
    """
    username = APP_USER
    pwd = PWD
    token = TOKEN
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
        token_list = nifty_50_data['token'].tolist()
        conn = http.client.HTTPSConnection("apiconnect.angelone.in")

        payload = {
            "mode": "FULL",
            "exchangeTokens": {
                "NSE": token_list
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
    
class HistoricalDataView(View):
    def get(self, request):
        # Authenticate and get tokens
        auth_token, feed_token = login()

        action = request.GET.get('action')
        if action == 'calculate_magic_number':
            return self.magic_number_response(request)
        else:
            return self.historical_data_response(request)

    def magic_number_response(self, request):
        result = calculate_magic_number_for_tickers(nifty_200)
        return JsonResponse(result, safe=False)

    def historical_data_response(self, request):
        thirty_days_ago = datetime.now() - timedelta(days=900)
        from_date = thirty_days_ago.strftime("%Y-%m-%d %H:%M")
        to_date = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Get parameters from request
        exchange = request.GET.get('exchange', 'NSE')  # Default is NSE
        token = request.GET.get('token', 1333)  # Default is 1333
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


# class TopGainersLosersView(View):
#     def get(self, request):
#         auth_token, feed_token = login()
#
#         gainers_params = {
#             "datatype": "PercPriceGainers",
#             "expirytype": "NEAR"
#         }
#         gainers = obj.gainersLosers(gainers_params)
#         time.sleep(0.5)
#         losers_params = {
#             "datatype": "PercPriceLosers",
#             "expirytype": "NEAR"
#         }
#         losers = obj.gainersLosers(losers_params)
#
#         return JsonResponse({
#             "status": "success",
#             "data": {
#                 "top_gainers": gainers['data'],
#                 "top_losers": losers['data']
#             }
#         }, status=200)


class TopGainersLosersView(View):
    def get(self, request):
        auth_token, feed_token = login()
        data = market_data(auth_token)
        stocks = json.loads(data)['data']['fetched']

        sorted_stocks = sorted(stocks, key=lambda x: x['percentChange'], reverse=True)

        top_gainers = sorted_stocks[:20]
        top_losers = sorted_stocks[-20:]

        return JsonResponse({
                "top_gainers": top_gainers,
                "top_losers": top_losers
            }, status=200)

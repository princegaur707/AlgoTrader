import asyncio
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
import json
from SmartApi import SmartConnect
from SmartApi.smartWebSocketV2 import SmartWebSocketV2
import pyotp
import threading
from logzero import logger
from service.constants import TOKEN, PWD, APP_USER, API_KEY
from service.utils import get_nifty_50_stocks, get_index_info

logger = logging.getLogger(__name__)


class AllNiftyFiftyConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        await self.accept()
        logger.info("WebSocket connection established for all Nifty 50 data")
        self.auth_token, self.feed_token = self.login()
        self.nifty_50_stocks = get_nifty_50_stocks()
        self.index_info = get_index_info()

        threading.Thread(target=self.initialize_websocket).start()

    async def disconnect(self, close_code):
        logger.info(f"WebSocket connection closed: {close_code}")
        self.sws.close_connection()

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        logger.info(f"Received message from WebSocket client: {message}")

    def login(self):
        obj = SmartConnect(api_key=API_KEY)
        data = obj.generateSession(APP_USER, PWD, pyotp.TOTP(TOKEN).now())
        refreshToken = data['data']['refreshToken']
        auth_token = data['data']['jwtToken']
        feed_token = obj.getfeedToken()
        return auth_token, feed_token

    def initialize_websocket(self):
        correlation_id = "nifty50_full"
        action = 1
        mode = 2

        nifty_tokens = self.nifty_50_stocks['token'].tolist()
        index_tokens = ["99926000", "99926009", "99926011"]
        token_list = [
            {"exchangeType": 1, "tokens": nifty_tokens + index_tokens},
            {"exchangeType": 3, "tokens": ["99919000"]}
        ]
        self.sws = SmartWebSocketV2(self.auth_token, API_KEY, APP_USER, self.feed_token, max_retry_attempt=5)

        def on_data(wsapp, message):
            try:
                token = message['token']
                if token in self.nifty_50_stocks['token'].values:
                    stock_info = self.nifty_50_stocks[self.nifty_50_stocks['token'] == token].iloc[0]
                    name = stock_info['name']
                    symbol = stock_info['symbol']
                    data_type = 'Stock'
                else:
                    index_details = self.index_info.get(token, {})
                    name = index_details.get('name', 'Unknown')
                    symbol = index_details.get('symbol', 'Unknown')
                    data_type = 'Index'

                last_traded_price = message['last_traded_price'] / 100
                closed_price = message['closed_price'] / 100
                volume = message['volume_trade_for_the_day']
                total_buy_quantity = message['total_buy_quantity']
                total_sell_quantity = message['total_sell_quantity']

                change = last_traded_price - closed_price
                change_percentage = (change / closed_price) * 100 if closed_price != 0 else 0

                formatted_data = {
                    'Type': data_type,
                    'Name': name,
                    'Symbol': symbol,
                    'LTP': f"{last_traded_price:.2f}",
                    'Change %': f"{change_percentage:.2f}%",
                    'Change': f"{change:.2f}",
                    'Volume': volume,
                    'Buy Quantity': total_buy_quantity,
                    'Sell Quantity': total_sell_quantity
                }

                logger.info(f"Formatted data: {formatted_data}")
                asyncio.run(self.send(json.dumps(formatted_data)))
            except Exception as e:
                logger.error(f"Error processing message: {e}")

        def on_open(wsapp):
            logger.info("WebSocket opened for all Nifty 50 data")
            self.sws.subscribe(correlation_id, mode, token_list)

        def on_error(wsapp, error):
            logger.error(f"WebSocket error: {error}")

        def on_close(*args, **kwargs):
            logger.info("WebSocket closed for all Nifty 50 data")

        self.sws.on_open = on_open
        self.sws.on_data = on_data
        self.sws.on_error = on_error
        self.sws.on_close = lambda *args, **kwargs: on_close(*args, **kwargs)

        self.sws.connect()

###ToDo: Replace _on_close function in smartWebSocketV2.py with this function:
"""
def _on_close(self, wsapp, close_status_code=None, close_msg=None):
    logger.info(f"WebSocket closed with status {close_status_code} and message {close_msg}")
    if hasattr(self, 'on_close'):
        self.on_close(wsapp)
"""

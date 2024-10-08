import asyncio
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
import json
from SmartApi import SmartConnect
from SmartApi.smartWebSocketV2 import SmartWebSocketV2
import pyotp, pytz
from datetime import datetime
import threading
from logzero import logger
from service.constants import TOKEN, PWD, APP_USER, API_KEY

logger = logging.getLogger(__name__)


class SmartAPILiveDataConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Accept the WebSocket connection
        await self.accept()
        logger.info("WebSocket connection established")
        self.auth_token, self.feed_token = self.login()

        # Start SmartAPI WebSocket in a thread
        threading.Thread(target=self.initialize_websocket).start()

    async def disconnect(self, close_code):
        logger.info(f"WebSocket connection closed: {close_code}")
        # Close the SmartAPI WebSocket connection when WebSocket disconnects
        self.sws.close_connection()

    async def receive(self, text_data):
        # Handling incoming messages from the client
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        logger.info(f"Received message from WebSocket client: {message}")

    def login(self):
        """
        Authenticate and return the AUTH and FEED tokens.
        """
        obj = SmartConnect(api_key=API_KEY)
        data = obj.generateSession(APP_USER, PWD, pyotp.TOTP(TOKEN).now())
        refreshToken = data['data']['refreshToken']
        auth_token = data['data']['jwtToken']
        feed_token = obj.getfeedToken()

        return auth_token, feed_token

    def initialize_websocket(self):
        correlation_id = "ws_test"
        action = 1  # 1: Subscribe
        mode = 2  # 2: Fetches quotes

        # Token list for indices
        # nifty50: 99926000, sensex: 99919000, banknifty: 99926009, nifty midcap 100: 99926011
        token_list = [
            {"exchangeType": 1, "tokens": ["99926000", "99926009", "99926011"]},
            {"exchangeType": 3, "tokens": ["99919000"]}
        ]

        self.sws = SmartWebSocketV2(self.auth_token, API_KEY, APP_USER, self.feed_token, max_retry_attempt=5)

        def on_data(wsapp, message):
            try:
                item = message
                timestamp = datetime.fromtimestamp(item['exchange_timestamp'] / 1000, pytz.timezone('Asia/Kolkata'))
                formatted_item = {
                    'Exchange Type': item['exchange_type'],
                    'Token': item['token'],
                    'Timestamp (IST)': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    'Open Price': f"{item['open_price_of_the_day'] / 100:.2f}",
                    'High Price': f"{item['high_price_of_the_day'] / 100:.2f}",
                    'Low Price': f"{item['low_price_of_the_day'] / 100:.2f}",
                    'Close Price': f"{item['closed_price'] / 100:.2f}",
                    'Last Traded Price': f"{item['last_traded_price'] / 100:.2f}",
                }
                logger.info(formatted_item)
                # Send data to WebSocket client
                asyncio.run(self.send(json.dumps(formatted_item)))
            except Exception as e:
                logger.error(f"Error processing message: {e}")

        def on_open(wsapp):
            logger.info("SmartAPI WebSocket opened")
            self.sws.subscribe(correlation_id, mode, token_list)

        def on_error(wsapp, error):
            logger.error(f"SmartAPI WebSocket error: {error}")

        def on_close(*args, **kwargs):
            logger.info("SmartAPI WebSocket closed")

        # Assign callbacks
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

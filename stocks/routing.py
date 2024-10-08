from django.urls import re_path
from service.consumers import SmartAPILiveDataConsumer, AllNiftyFiftyConsumer

websocket_urlpatterns = [
    re_path(r'ws/stock-indices-feed/', SmartAPILiveDataConsumer.as_asgi()),
    re_path(r'ws/nifty50-feed/', AllNiftyFiftyConsumer.as_asgi()),
]

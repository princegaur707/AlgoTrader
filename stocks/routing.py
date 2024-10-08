from django.urls import re_path
from service.consumers import SmartAPILiveDataConsumer

websocket_urlpatterns = [
    re_path(r'ws/live-market-feed/', SmartAPILiveDataConsumer.as_asgi()),
]

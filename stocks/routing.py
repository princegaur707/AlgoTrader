from django.urls import re_path
from service.consumers import AllNiftyFiftyConsumer

websocket_urlpatterns = [
    re_path(r'ws/nifty50-feed/', AllNiftyFiftyConsumer.as_asgi()),
]

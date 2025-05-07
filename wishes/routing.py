from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path("ws/wishes/", consumers.WishConsumer.as_asgi()),
]
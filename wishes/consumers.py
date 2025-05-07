import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Wish
from .serializers import WishSerializer

import logging
logger = logging.getLogger(__name__)

class WishConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = "wishes"
        print(f"Verbindung zu Gruppe {self.group_name} wird hinzugefügt...")
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        print(f"WebSocket verbunden: {self.channel_name}")
        await self.accept()
        await self.send_wishes()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        print(f"❌ WebSocket aus Gruppe {self.group_name} entfernt.")

    @database_sync_to_async
    def get_wishes(self):
        wishes = Wish.objects.all()
        serializer = WishSerializer(wishes, many=True)
        return serializer.data

    async def send_wishes(self):
        data = await self.get_wishes()
        await self.send(text_data=json.dumps(data))

    async def wish_update(self, event):
        print(f"🎯 Event empfangen: {event}")
        # Wünsche an den Client senden
        await self.send_wishes()
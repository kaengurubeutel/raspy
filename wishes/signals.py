from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Wish
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

@receiver([post_save, post_delete], sender=Wish)
def push_wish_update(sender, **kwargs):
    print("🔥 Signal ausgelöst! Wünsche werden gesendet...")
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "wishes",  # Die Gruppe, die der Consumer abonniert hat
        {"type": "wish.update"}  # Event-Typ
    )
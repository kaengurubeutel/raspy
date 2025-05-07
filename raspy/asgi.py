"""
ASGI config for raspy project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""
# raspy/asgi.py

import os
import django
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application


# Stelle sicher, dass DJANGO_SETTINGS_MODULE gesetzt ist
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "raspy.settings")

# Django Setup durchführen
django.setup()  # <- Hier sicherstellen, dass es korrekt platziert ist!
import wishes.routing  # Korrekt auf das Routing in der wishes-App verweisen!
application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": URLRouter(wishes.routing.websocket_urlpatterns),  # routing aus der wishes-App
})

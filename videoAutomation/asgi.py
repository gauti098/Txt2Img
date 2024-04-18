"""
ASGI config for videoAutomation project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/howto/deployment/asgi/
"""

# import os

# from django.core.asgi import get_asgi_application

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'videoAutomation.settings')

# application = get_asgi_application()
import os,django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'videoAutomation.settings')
django.setup()
from django.urls import path
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator, OriginValidator
from django.core.asgi import get_asgi_application
from videoAutomation.tokenAuthWebsocket import TokenAuthMiddlewareStack
from campaignAnalytics.consumers import NotificationConsumer
from electronThumbnail.consumers import SetThumbnailConsumer
from newVideoCreator.consumers import NewVideoCreatorConsumer


application = ProtocolTypeRouter({ 
    "http": get_asgi_application(),
    # Websocket chat handler
    'websocket': TokenAuthMiddlewareStack(
            URLRouter(
                [
                    path("notifications/", NotificationConsumer.as_asgi()),
                    path("ws/setthumbnail/", SetThumbnailConsumer.as_asgi()),
                    path("ws/app/video/", NewVideoCreatorConsumer.as_asgi()),
                ]
            )
    ),
})


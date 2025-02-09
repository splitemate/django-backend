"""
routing for web socket
"""

from django.urls import re_path
from core.consumers import CoreConsumer, NotFoundConsumer

websocket_urlpatterns = [
    re_path(r'ws/socket/?$', CoreConsumer.as_asgi()),
    re_path(r".*", NotFoundConsumer.as_asgi())
]

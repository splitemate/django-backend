"""
routing for web socket
"""

from django.urls import re_path
from transaction.consumers import TransactionConsumer

websocket_urlpatterns = [
    re_path(r'ws/transaction/?$', TransactionConsumer.as_asgi()),
]

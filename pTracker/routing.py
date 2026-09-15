# from django.urls import path
# from .consumers import PTrackerWebSocketConsumer

# websocket_urlpatterns = [
#     path('ws/ptracker/', PTrackerWebSocketConsumer.as_asgi()),
# ]


# pTracker/routing.py

# from django.urls import path
# from channels.routing import ProtocolTypeRouter, URLRouter
# from channels.auth import AuthMiddlewareStack
# from .consumers import PTrackerWebSocketConsumer

# application = ProtocolTypeRouter({
#     'websocket': AuthMiddlewareStack(
#         URLRouter([
#             path('ws/ptracker/', PTrackerWebSocketConsumer.as_asgi()),
#         ])
#     ),
# })


# pTracker/routing.py

from django.urls import path
from .consumers import PTrackerWebSocketConsumer

websocket_urlpatterns = [
    path('ws/ptracker/', PTrackerWebSocketConsumer.as_asgi()),
    # Add other WebSocket URL patterns if needed
]

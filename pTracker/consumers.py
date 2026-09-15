
# from pTracker.api.rewards.rewards_biz import RewardsBL

# from channels.generic.websocket import WebsocketConsumer
# from channels.layers import get_channel_layer
# from asgiref.sync import async_to_sync
# import json

# class PTrackerWebSocketConsumer(WebsocketConsumer):
#     def connect(self):
#         self.accept()

#         # Connect the consumer to the 'my_group' group
#         async_to_sync(self.channel_layer.group_add)('my_group', self.channel_name)

#     def disconnect(self, close_code):
#         # Disconnect the consumer from the 'my_group' group
#         async_to_sync(self.channel_layer.group_discard)('my_group', self.channel_name)

#     # def receive(self, text_data):
#     #     # You can handle incoming WebSocket messages here
#     #     # For this example, we'll just respond to the client
#     #     response_data = RewardsBL().get_tv_notifications_v1()
#     #     self.send(text_data=json.dumps(response_data))
    
#     def receive(self, text_data):
#         data = json.loads(text_data)
#         if 'type' in data and data['type'] == 'join_group':
#             # Add the consumer to the requested group
#             group_name = data.get('group', '')
#             if group_name:
#                 async_to_sync(self.channel_layer.group_add)(group_name, self.channel_name)
#         else:
#             # You can handle other incoming WebSocket messages here
#             # For this example, we'll just respond to the client
#             response_data = RewardsBL().get_tv_notifications_v1()
#             self.send(text_data=json.dumps(response_data))

#     async def send_notification(self, event):
#         # This method will be called whenever you push data to the WebSocket clients

#         # Get the data you want to send from the event
#         notification_data = event.get('data', None)

#         if notification_data:
#             # Send the data to the client
#             await self.send(text_data=json.dumps(notification_data))


# myapp/consumers.py

# import json
# from channels.generic.websocket import AsyncWebsocketConsumer

# class PTrackerWebSocketConsumer(AsyncWebsocketConsumer):
#     async def connect(self):
#         # Perform any initial setup or checks here
#         await self.accept()

#     async def disconnect(self, close_code):
#         # Clean up resources if needed
#         pass

#     async def receive(self, text_data):
#         # Handle incoming WebSocket messages
#         # For live updates, you may want to broadcast this message to all connected clients.
#         pass


# myapp/consumers.py

# consumers.py

from pTracker.api.rewards.rewards_biz import RewardsBL


# import json
# from channels.generic.websocket import AsyncWebsocketConsumer

# class PTrackerWebSocketConsumer(AsyncWebsocketConsumer):
#     async def connect(self):
#         # Perform any initial setup or checks here
#         await self.accept()

#     async def disconnect(self, close_code):
#         # Clean up resources if needed
#         pass

#     async def receive(self, text_data):
#         # Handle incoming WebSocket messages
#         # For live updates, you may want to broadcast this message to all connected clients.
#         pass

#     async def send_live_update(self):
#         # Send a live update to the connected WebSocket clients
#         response_data = RewardsBL().get_tv_notifications_v1()
#         await self.send(text_data=json.dumps(response_data))


import json
from channels.generic.websocket import AsyncWebsocketConsumer

class PTrackerWebSocketConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Perform any initial setup or checks here
        await self.accept()

        # Add the connected user to a group
        await self.channel_layer.group_add(
            'tv_group',  # Replace with the same group name used in views.py
            self.channel_name
        )

    async def disconnect(self, close_code):
        # Clean up resources if needed
        # Remove the connected user from the group
        await self.channel_layer.group_discard(
            'tv_group',  # Replace with the same group name used in views.py
            self.channel_name
        )

    async def receive(self, text_data):
        # Handle incoming WebSocket messages
        pass

    async def send_live_update(self, event):
        # Send a live update to the connected WebSocket clients
        live_update_data = event['data']#RewardsBL().get_tv_notifications_v1()
        await self.send(text_data=json.dumps(live_update_data))
        
        
        
import json
from channels.generic.websocket import AsyncWebsocketConsumer

class SeatBookingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.show_id = self.scope['url_route']['kwargs']['show_id']
        self.room_group_name = f"show_{self.show_id}"

        # Join group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Leave group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        data = json.loads(text_data)
        # Broadcast to group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'seat_update',
                'seat_id': data['seat_id'],
                'status': data['status']
            }
        )

    # Handle group message
    async def seat_update(self, event):
        await self.send(text_data=json.dumps({
            'seat_id': event['seat_id'],
            'status': event['status']
        }))

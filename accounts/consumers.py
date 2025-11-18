# consumers.py
from channels.generic.websocket import AsyncWebsocketConsumer
import json

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        from channels.db import database_sync_to_async
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        self.sender = self.scope["user"]
        print("Connected user:", self.sender)
        self.receiver_username = self.scope['url_route']['kwargs']['username']
        print("Chatting with:", self.receiver_username)

        # Get the receiver User object
        self.receiver = await database_sync_to_async(User.objects.get)(username=self.receiver_username)

        # Generate a consistent room name for 1-to-1 chat
        self.room_group_name = f'chat_{min(self.sender.id, self.receiver.id)}_{max(self.sender.id, self.receiver.id)}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        from channels.db import database_sync_to_async
        from .models import Message

        text_data_json = json.loads(text_data)
        message_content = text_data_json['message']

        # Save message to DB
        sender = self.sender
        receiver = self.receiver  # use the receiver object you already fetched

        message = await database_sync_to_async(Message.objects.create)(
            sender=sender,
            receiver=receiver,
            content=message_content
        )

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message.content,
                'sender': sender.username,
                'receiver': receiver.username,
                'timestamp': message.timestamp.isoformat()
            }
        )

    async def chat_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'sender': event['sender'],
            'receiver': event['receiver'],
            'timestamp': event['timestamp']
        }))

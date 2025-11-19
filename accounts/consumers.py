# consumers.py
from channels.generic.websocket import AsyncWebsocketConsumer
import json

class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        from channels.db import database_sync_to_async
        from django.contrib.auth import get_user_model
        from .models import Message

        User = get_user_model()

        self.sender = self.scope["user"]
        print("Connected user:", self.sender)
        self.receiver_username = self.scope['url_route']['kwargs']['username']
        print("Chatting with:", self.receiver_username)

        # Load receiver
        self.receiver = await database_sync_to_async(User.objects.get)(username=self.receiver_username)

        # Create 1-to-1 stable room name
        self.room_group_name = f'chat_{min(self.sender.id, self.receiver.id)}_{max(self.sender.id, self.receiver.id)}'

        # Join room
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # MARK ALL MESSAGES FROM RECEIVER TO THIS USER AS READ
        await database_sync_to_async(
            Message.objects.filter(
                sender=self.receiver,
                receiver=self.sender,
                is_read=False
            ).update
        )(is_read=True)

        # Send read receipt update to the other user
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "read_receipt",
                "reader": self.sender.username,
                "partner": self.receiver.username
            }
        )

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        from channels.db import database_sync_to_async
        from .models import Message

        data = json.loads(text_data)
        msg_content = data["message"]

        sender = self.sender
        receiver = self.receiver

        # Save message to DB
        message = await database_sync_to_async(Message.objects.create)(
            sender=sender,
            receiver=receiver,
            content=msg_content,
            is_read=False  # New messages are unread initially
        )

        # Broadcast new message
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": message.content,
                "sender": sender.username,
                "receiver": receiver.username,
                "timestamp": message.timestamp.isoformat(),
                "id": message.id,
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "id": event["id"],
            "message": event["message"],
            "sender": event["sender"],
            "receiver": event["receiver"],
            "timestamp": event["timestamp"]
        }))

    async def read_receipt(self, event):
        """
        Notify both clients that messages have been marked as read.
        This helps update unread counters in the UI.
        """
        await self.send(text_data=json.dumps({
            "type": "read_receipt",
            "reader": event["reader"],      # the user who read the messages
            "partner": event["partner"]     # the other user
        }))

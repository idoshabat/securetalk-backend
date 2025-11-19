# consumers.py
from channels.generic.websocket import AsyncWebsocketConsumer
import json

# track active users in chats per server instance
active_chats = {}  # key: room_group_name, value: set of usernames connected


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        from channels.db import database_sync_to_async
        from django.contrib.auth import get_user_model
        from .models import Message

        User = get_user_model()

        self.sender = self.scope["user"]
        self.receiver_username = self.scope['url_route']['kwargs']['username']
        self.receiver = await database_sync_to_async(User.objects.get)(username=self.receiver_username)

        # stable 1-to-1 room name
        self.room_group_name = f'chat_{min(self.sender.id, self.receiver.id)}_{max(self.sender.id, self.receiver.id)}'

        # join WebSocket group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # mark this user as active in this chat
        active_chats.setdefault(self.room_group_name, set()).add(self.sender.username)

        # mark all delivered messages from receiver as seen if this user has the chat open
        await database_sync_to_async(
            Message.objects.filter(sender=self.receiver, receiver=self.sender, status="delivered").update
        )(status="seen")

        # notify the other user that this user read all messages
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "read_receipt",
                "reader": self.sender.username,
                "partner": self.receiver.username
            }
        )

    async def disconnect(self, close_code):
        # remove from active chat tracking
        if self.room_group_name in active_chats:
            active_chats[self.room_group_name].discard(self.sender.username)
            if not active_chats[self.room_group_name]:
                del active_chats[self.room_group_name]

        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        from channels.db import database_sync_to_async
        from .models import Message

        data = json.loads(text_data)
        message_content = data['message']
        temp_id = data.get("tempId")

        # Determine initial status
        if self.room_group_name in active_chats and self.receiver.username in active_chats[self.room_group_name]:
            initial_status = "seen"
        else:
            initial_status = "delivered"

        # Save message
        message = await database_sync_to_async(Message.objects.create)(
            sender=self.sender,
            receiver=self.receiver,
            content=message_content,
            status=initial_status
        )

        # Broadcast message
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "id": message.id,
                "message": message.content,
                "sender": self.sender.username,
                "receiver": self.receiver.username,
                "timestamp": message.timestamp.isoformat(),
                "status": initial_status,
                "tempId": temp_id
            }
        )

        # If receiver is active, also broadcast read_receipt immediately
        if initial_status == "seen":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "read_receipt",
                    "reader": self.receiver.username,
                    "partner": self.sender.username
                }
            )

    async def chat_message(self, event):
        # send message to WebSocket
        await self.send(text_data=json.dumps({
            "id": event["id"],
            "message": event["message"],
            "sender": event["sender"],
            "receiver": event["receiver"],
            "timestamp": event["timestamp"],
            "status": event.get("status", "sent"),
            "tempId": event.get("tempId")
        }))

    async def read_receipt(self, event):
        # notify frontend that messages have been seen
        await self.send(text_data=json.dumps({
            "type": "read_receipt",
            "reader": event["reader"],
            "partner": event["partner"]
        }))

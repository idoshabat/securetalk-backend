from channels.generic.websocket import AsyncWebsocketConsumer
import json

active_chats = {}  # Keeps track of active users in each chat

class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        from channels.db import database_sync_to_async
        from django.contrib.auth import get_user_model
        from .models import Message

        User = get_user_model()
        self.sender = self.scope["user"]
        self.receiver_username = self.scope['url_route']['kwargs']['username']
        self.receiver = await database_sync_to_async(User.objects.get)(
            username=self.receiver_username
        )

        # Unique chat room between two users
        self.room_group_name = (
            f'chat_{min(self.sender.id, self.receiver.id)}_{max(self.sender.id, self.receiver.id)}'
        )

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        active_chats.setdefault(self.room_group_name, set()).add(self.sender.username)

        # Mark delivered messages as seen on connect
        delivered_messages = await database_sync_to_async(list)(
            Message.objects.filter(
                sender=self.receiver,
                receiver=self.sender,
                status="delivered"
            ).values_list("id", flat=True)
        )

        if delivered_messages:
            await database_sync_to_async(
                Message.objects.filter(id__in=delivered_messages).update
            )(status="seen")

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "read_receipt",
                    "reader": self.sender.username,
                    "ids": list(delivered_messages)
                }
            )

    async def disconnect(self, close_code):
        if self.room_group_name in active_chats:
            active_chats[self.room_group_name].discard(self.sender.username)
            if not active_chats[self.room_group_name]:
                del active_chats[self.room_group_name]

        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)

        # ---------------------------------------------------------
        # TYPING EVENTS
        # ---------------------------------------------------------
        if data.get("type") == "typing":
            await self.channel_layer.group_send(
                self.room_group_name,
                {"type": "typing_event", "username": self.sender.username, "typing": True}
            )
            return

        if data.get("type") == "stop_typing":
            await self.channel_layer.group_send(
                self.room_group_name,
                {"type": "typing_event", "username": self.sender.username, "typing": False}
            )
            return

        # ---------------------------------------------------------
        # READ RECEIPTS (NEW)
        # ---------------------------------------------------------
        if data.get("type") == "read_messages":
            ids = data.get("ids", [])

            from channels.db import database_sync_to_async
            from .models import Message

            await database_sync_to_async(
                Message.objects.filter(id__in=ids).update
            )(status="seen")

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "read_receipt",
                    "reader": self.sender.username,
                    "ids": ids
                }
            )
            return

        # ---------------------------------------------------------
        # HANDLE NEW MESSAGE
        # ---------------------------------------------------------
        from channels.db import database_sync_to_async
        from .models import Message

        message_content = data["message"]
        temp_id = data.get("tempId")

        # If receiver is active in chat => message is instantly "seen"
        initial_status = (
            "seen"
            if (self.room_group_name in active_chats and
                self.receiver.username in active_chats[self.room_group_name])
            else "delivered"
        )

        message = await database_sync_to_async(Message.objects.create)(
            sender=self.sender,
            receiver=self.receiver,
            content=message_content,
            status=initial_status
        )

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

        # If instantly seen, notify both sides
        if initial_status == "seen":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "read_receipt",
                    "reader": self.receiver.username,
                    "ids": [message.id]
                }
            )

    # ---------------------------------------------------------
    # SENDERS FOR EVENTS
    # ---------------------------------------------------------

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    async def read_receipt(self, event):
        await self.send(text_data=json.dumps(event))

    async def typing_event(self, event):
        await self.send(text_data=json.dumps({
            "type": "typing",
            "username": event["username"],
            "typing": event["typing"]
        }))

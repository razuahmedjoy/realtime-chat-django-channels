from channels.generic.websocket import AsyncWebsocketConsumer
import json
from .models import Chat, Message
from channels.db import database_sync_to_async
from django.contrib.auth.models import User

class ChatConsumer(AsyncWebsocketConsumer):
   
    async def connect(self):
  
        self.chat_id = self.scope['url_route']['kwargs']['chat_id']
        print("Self : ",self.scope)
        self.chat_group_name = f'chat_{self.chat_id}'
        await self.channel_layer.group_add(self.chat_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.chat_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        event_type = data["type"]

        if event_type == "message":
        
            message = data["message"]
            sender_id = self.scope["user"].id
            # print(sender_id)
            # Fetch the chat and sender asynchronously
            chat = await database_sync_to_async(Chat.objects.get)(id=self.chat_id)
            sender = await database_sync_to_async(User.objects.get)(id=sender_id)

            # Create the message asynchronously
            await database_sync_to_async(Message.objects.create)(chat=chat, sender=sender, text=message)

            # Send the message to the WebSocket group
            await self.channel_layer.group_send(
                self.chat_group_name,
                {
                    "type": "chat_message",
                    "message": message,
                    "sender": sender.id,
                }
            )
        elif event_type == "typing":
            typing_status = data["is_typing"]
            sender = self.scope["user"].username
            await self.channel_layer.group_send(
                self.chat_group_name,
                {
                    "type": "chat_typing",
                    "is_typing": typing_status,
                    "sender": sender,
                }
            )


    async def chat_message(self, event):
        message = event["message"]
        sender = event["sender"]

        await self.send(text_data=json.dumps({
            "type": "message",
            "text": message,
            "sender": sender,
        }))

    async def chat_typing(self, event):
        is_typing = event["is_typing"]
        sender = event["sender"]

        await self.send(text_data=json.dumps({
            "type": "typing",
            "is_typing": is_typing,
            "sender": sender,
        }))

from channels.generic.websocket import AsyncWebsocketConsumer
import json
from .models import Chat, Message, KeyPair
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from base64 import b64encode, b64decode
from chat.utils import hybrid_decrypt_audio


class ChatConsumer(AsyncWebsocketConsumer):
   
    async def connect(self):
  
        self.chat_id = self.scope['url_route']['kwargs']['chat_id']
        # print("Self : ",self.scope)
        self.chat_group_name = f'chat_{self.chat_id}'
        await self.channel_layer.group_add(self.chat_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.chat_group_name,
            self.channel_name
        )
    
    def encrypt_message(self, public_key_str, message):
        public_key = RSA.import_key(public_key_str)
        cipher = PKCS1_OAEP.new(public_key)
        chunk_size = 190  # Max size depends on the key size and padding
        chunks = [message[i:i + chunk_size] for i in range(0, len(message), chunk_size)]
        
        encrypted_chunks = [b64encode(cipher.encrypt(chunk.encode())) for chunk in chunks]
        return '||'.join([chunk.decode('utf-8') for chunk in encrypted_chunks])

    async def get_user_by_email(self, email):
        return await User.objects.get(email=email)

    async def receive(self, text_data):
        data = json.loads(text_data)
        event_type = data["type"]

        if event_type == "message":
        
            message = data["message"]
            sender_id = self.scope["user"].id
            recipient_id = data["recipient"]

            # print(sender_id)
            # Fetch the chat and sender asynchronously
            chat = await database_sync_to_async(Chat.objects.get)(id=self.chat_id)
            sender = await database_sync_to_async(User.objects.get)(id=sender_id)

            # public_key = await database_sync_to_async(KeyPair.objects.get)(user=recipient_id)
            # public_key = public_key.public_key

            # get public key of the current chat
            public_key = chat.public_key

            # encrypt the message
            encrypted_message = self.encrypt_message(public_key, message)


            # Create the message asynchronously
            await database_sync_to_async(Message.objects.create)(chat=chat, sender=sender, text=encrypted_message)

            # Send the message to the WebSocket group
            await self.channel_layer.group_send(
                self.chat_group_name,
                {
                    "type": "chat_message",
                    "message": message,
                    "sender": sender.id,
                    "recipient": recipient_id,
                }
            )

        elif event_type == "voice_message":

            sender_id = self.scope["user"].id
            recipient_id = data["recipient"]
            
            await self.channel_layer.group_send(
                self.chat_group_name,
                {
                    "type": "voice_message",
                    "voice_url": data["voice_url"],
                    "sender": sender_id,
                    "recipient": recipient_id,
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

        elif event_type == "stream_audio":
            message_id = data.get('message_id')

            if message_id:
                try:
                    # Fetch the message from the database
                    message = await database_sync_to_async(Message.objects.get)(id=message_id)

                    if message and message.voice_message:
                        # Decrypt the audio file
                        with open(message.voice_message.path, 'rb') as f:
                            ciphertext = f.read()

                        private_key = message.chat.private_key
                        # private key in pem format
                        private_key_pem = RSA.import_key(private_key) # Import the private key

                        decrypted_audio = hybrid_decrypt_audio(
                            message.encrypted_key,
                            ciphertext,
                            message.nonce,
                            message.tag,
                            private_key_pem
                        )

                        # Send the decrypted audio as a base64 string
                        await self.send(json.dumps({
                            "type": "audio_message",
                            "audio_data": decrypted_audio.hex()  # Convert binary to hex for transmission
                        }))
                        
                except Exception as e:
                    # Send error message to WebSocket
                    await self.send(json.dumps({"error": str(e)}))

    async def chat_message(self, event):
        message = event["message"]
        sender = event["sender"]

        await self.send(text_data=json.dumps({
            "type": "message",
            "text": message,
            "voice_url": "",
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

    async def voice_message(self, event):
        voice_url = event["voice_url"]
        sender = event["sender"]

        await self.send(text_data=json.dumps({
            "type": "voice_message",
            "text": "",
            "voice_url": voice_url,
            "sender": event["sender"],
        }))
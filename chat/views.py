from django.contrib.auth.models import User
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Chat, Message, KeyPair
from .serializers import MessageSerializer
from chat.utils import generate_key_pair, hybrid_decrypt_audio, hybrid_encrypt_audio
from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from base64 import b64encode, b64decode
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from django.http import HttpResponseNotFound, StreamingHttpResponse
import os
import uuid
from django.http import HttpResponse


def decrypt_message(private_key_str, encrypted_message):
    private_key = RSA.import_key(private_key_str)
    cipher = PKCS1_OAEP.new(private_key)
    
    # Split the encrypted message into chunks
    encrypted_chunks = encrypted_message.split('||')
    decrypted_chunks = [cipher.decrypt(b64decode(chunk.encode())).decode('utf-8') for chunk in encrypted_chunks]
    return ''.join(decrypted_chunks)


@api_view(["GET"])
def search_users(request):
    query = request.GET.get("email", "")
    users = User.objects.filter(email__icontains=query).exclude(id=request.user.id)
    results = [{"id": user.id, "email": user.email} for user in users]
    return Response(results)

@api_view(["POST"])
def start_chat(request):

    user_id = request.data.get("user_id")
    other_user = User.objects.get(id=user_id)
    chat = Chat.objects.filter(participants=request.user).filter(participants=other_user).first()
    if not chat:
        chat = Chat.objects.create()
        private_key, public_key = generate_key_pair()
        
        chat.participants.add(request.user, other_user)
        chat.private_key = private_key
        chat.public_key = public_key
        chat.save()
    # check if the chat already exists but the public key is not set
    elif not chat.public_key:
        private_key, public_key = generate_key_pair()
        chat.private_key = private_key
        chat.public_key = public_key
        chat.save()
    
    # add username or email to the response
    chat_data = {}
    chat_data["chat_id"] = chat.id
    chat_data["participants"] = [participant.id for participant in chat.participants.all()]
    chat_data['current_user'] = request.user.username
    chat_data['current_user_id'] = request.user.id
    chat_data['other_user'] = [participant.username for participant in chat.participants.all() if participant.username != request.user.username]
    return Response(chat_data)

@api_view(["GET"])
def get_chat_messages(request, chat_id):
    try:
        chat = Chat.objects.get(id=chat_id)
    except Chat.DoesNotExist:
        return Response({"error": "Chat not found."}, status=404)

    # Fetch messages for the given chat
    messages = Message.objects.filter(chat=chat).order_by("timestamp")
    private_key = chat.private_key
    
    # Create a list to store decrypted messages with voice URLs
    decrypted_messages = []
    for message in messages:
        # Get the private key of the chat for decryption
        decrypted_text = ""
        voice_url = ""

        # Decrypt the text message if it exists
        if message.text:
            decrypted_text = decrypt_message(private_key, message.text)

        # Decrypt and prepare the voice message if it exists
        if message.voice_message:
            # Path to the encrypted voice message
            encrypted_voice_path = message.voice_message.path

            with open(encrypted_voice_path, "rb") as f:
                ciphertext = f.read()

            # Decrypt the audio file
            decrypted_voice_path = hybrid_decrypt_audio(
                message.encrypted_key,
                ciphertext,
                message.nonce,
                message.tag,
                private_key
            )
       
            # Assuming media is served from the MEDIA_URL path in Django settings
            voice_url = f'http://127.0.0.1:8000/api/chat/stream_audio/{message.id}/'

        # Add the decrypted message to the list
        decrypted_messages.append({
            "id": message.id,
            "sender": message.sender.id,
            "text": decrypted_text,
            "voice_url": voice_url,  # Add the decrypted voice URL here
            "timestamp": message.timestamp.isoformat(),
        })

    # Return the decrypted messages as a response
    return Response(decrypted_messages, status=200)



@api_view(["GET"])
def get_chats(request):
    chats = Chat.objects.filter(participants=request.user)
    results = []
    for chat in chats:
        chat_data = {}
        chat_data["chat_id"] = chat.id
        chat_data["participants"] = [participant.id for participant in chat.participants.all()]
        chat_data['current_user'] = request.user.username
        chat_data['current_user_id'] = request.user.id
        chat_data['other_user'] = [participant.username for participant in chat.participants.all() if participant.username != request.user.username]
        results.append(chat_data)
    return Response(results)




@csrf_exempt
def upload_voice_message(request):
    if request.method == 'POST' and request.FILES.get('voice_message'):

        chat_id = request.POST.get('chat_id')
        sender_id = request.POST.get('sender_id')
        chat = Chat.objects.get(id=chat_id)
        sender = User.objects.get(id=sender_id)
        voice_message = request.FILES["voice_message"]

        audio_data = voice_message.read()
        public_key = chat.public_key

        if not voice_message or not audio_data:
            return JsonResponse({'error': 'No voice message found'}, status=400)

        # need to pass the public key in pem format
        public_key_pem = RSA.import_key(public_key).export_key()

        # Encrypt the audio file using hybrid encryption

        encrypted_aes_key, ciphertext, nonce, tag = hybrid_encrypt_audio(audio_data, public_key_pem)

        # Save the encrypted audio file
        encrypted_file_name = f"encrypted_{voice_message.name}"
        encrypted_file_path = os.path.join("voice_messages", encrypted_file_name)
        full_encrypted_file_path = os.path.join(settings.MEDIA_ROOT, encrypted_file_path)


        with open(full_encrypted_file_path, "wb") as f:
            f.write(ciphertext)
        

        # Save message
        message = Message.objects.create(
            chat=chat,
            sender=sender,
            voice_message=encrypted_file_path,
            encrypted_key=encrypted_aes_key,
            nonce=nonce,
            tag=tag
        )
        # Construct the voice URL with server URL
       
        # voice_url = f'http://127.0.0.1:8000/media/{message.voice_message.name}'
        return JsonResponse({
            'message': 'Voice message sent successfully',
            'id': message.id,
            'sender': message.sender.username,
            'chat': message.chat.id,
            'voice_url': encrypted_file_path,

            'timestamp': message.timestamp
        })

    return JsonResponse({'error': 'Invalid request'}, status=400)


from django.http import FileResponse
from django.conf import settings
import os

@csrf_exempt
def serve_audio_file(request, file_name):
    file_path = os.path.join(settings.MEDIA_ROOT, "voice_messages", file_name)
    
    if os.path.exists(file_path):
        # Determine MIME type based on file extension or content type
        mime_type = 'audio/webm'  # Change this to the correct MIME type, if needed
        response = FileResponse(open(file_path, 'rb'), content_type=mime_type)
        return response
    else:
        return HttpResponseNotFound("File not found.")


@csrf_exempt
def stream_audio(request, message_id):
    try:
        # Get the message instance
        message = Message.objects.get(id=message_id)

        # Read encrypted audio file
        file_path = message.voice_message.path
        with open(file_path, "rb") as f:
            ciphertext = f.read()

        # Decrypt the audio using hybrid decryption
        private_key = message.chat.private_key
        decrypted_audio = hybrid_decrypt_audio(
            message.encrypted_key,
            ciphertext,
            message.nonce,
            message.tag,
            private_key
        )

        # Stream the decrypted audio
        response = StreamingHttpResponse(decrypted_audio, content_type="audio/mpeg")
        response["Content-Disposition"] = f'inline; filename="{message.voice_message.name}"'
        return response

    except Message.DoesNotExist:
        raise Http404("Message not found")
    except FileNotFoundError:
        raise Http404("File not found")
from django.contrib.auth.models import User
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Chat, Message, KeyPair
from .serializers import MessageSerializer
from chat.utils import generate_key_pair, decrypt_message, decrypt_final_audio
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from django.http import HttpResponseNotFound, StreamingHttpResponse
import os
import uuid
from django.http import HttpResponse

import base64




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

    messages = Message.objects.filter(chat=chat).order_by("timestamp")
    private_key = chat.private_key

    decrypted_messages = []

    for message in messages:
        decrypted_text = ""
        decrypted_audio = None

        if message.text:
            decrypted_text = decrypt_message(private_key,message.text)

        if message.encrypted_aes_key:
            decrypted_audio = decrypt_final_audio(message.encrypted_audio, message.encrypted_aes_key, message.iv, private_key)

        decrypted_messages.append({
            "id": message.id,
            "sender": message.sender.id,
            "text": decrypted_text,
            "voice_url": decrypted_audio,  
            "timestamp": message.timestamp.isoformat(),
        })

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
        # add public key of this chat 
        chat_data["public_key"] = chat.public_key
        chat_data["private_key"] = chat.private_key
        results.append(chat_data)
    return Response(results)





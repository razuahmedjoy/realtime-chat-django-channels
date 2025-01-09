from django.contrib.auth.models import User
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Chat, Message
from .serializers import MessageSerializer

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
        chat.participants.add(request.user, other_user)
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
    serializer = MessageSerializer(messages, many=True)
    return Response(serializer.data)

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
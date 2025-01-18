from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import search_users, start_chat, get_chat_messages, get_chats, upload_voice_message, serve_audio_file, stream_audio

urlpatterns = [
    path("search_users/", search_users, name="search_users"),
    path("start_chat/", start_chat, name="start_chat"),
    path("<int:chat_id>/messages/", get_chat_messages, name="get_chat_messages"),
    # get all chats of the current user with other users
    path("chats/", get_chats, name="get_chats"),
    path('upload-voice/', upload_voice_message, name='upload_voice_message'),
    path('voice_messages/<str:file_name>/', serve_audio_file, name='serve_audio_file'),
    path('stream_audio/<int:message_id>/', stream_audio, name='stream_audio'),


]

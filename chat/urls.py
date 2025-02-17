from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import search_users, start_chat, get_chat_messages, get_chats
urlpatterns = [

    path("chats/", get_chats, name="get_chats"),
    path("search_users/", search_users, name="search_users"),
    
    path("start_chat/", start_chat, name="start_chat"),



    path("<int:chat_id>/messages/", get_chat_messages, name="get_chat_messages"),
    


]

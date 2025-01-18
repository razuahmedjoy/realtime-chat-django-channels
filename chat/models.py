
# Create your models here.
from django.contrib.auth.models import User
from django.db import models


class KeyPair(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    public_key = models.TextField()
    private_key = models.TextField()
class Chat(models.Model):
    participants = models.ManyToManyField(User, related_name="chats")
    public_key = models.TextField(null=True)
    private_key = models.TextField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Message(models.Model):
    chat = models.ForeignKey(Chat, related_name="messages", on_delete=models.CASCADE)
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    voice_message = models.FileField(upload_to="voice_messages/", blank=True, null=True)
    encrypted_key = models.BinaryField(blank=True, null=True)  # RSA-encrypted AES key
    nonce = models.BinaryField(blank=True, null=True)  # AES nonce
    tag = models.BinaryField(blank=True, null=True)  # AES tag
    timestamp = models.DateTimeField(auto_now_add=True)

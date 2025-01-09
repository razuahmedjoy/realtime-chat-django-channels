from django.contrib import admin

# Register your models here.

from .models import Chat, Message

admin.site.register(Chat)


# show the message model in the admin panel and show all the fields in the message model
class MessageAdmin(admin.ModelAdmin):
    list_display = ['chat', 'sender', 'text', 'timestamp']
    list_filter = ['chat', 'sender', 'timestamp']
    search_fields = ['chat', 'sender', 'text']

admin.site.register(Message, MessageAdmin)
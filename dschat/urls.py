from django.contrib import admin
from django.urls import path
from chat_app import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('stream_response/', views.stream_response, name='stream_response'),
    path('create_conversation/', views.create_conversation, name='create_conversation'),
    path('get_conversation_messages/<int:conversation_id>/', views.get_conversation_messages, name='get_conversation_messages'),
    path('delete_all_conversations/', views.delete_all_conversations, name='delete_all_conversations'),
]

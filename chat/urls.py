from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_list, name='chat_list'),
    path('<int:room_id>/', views.chat_room, name='chat_room'),
    path('<int:room_id>/send/', views.send_message, name='send_message'),
    path('attachments/<int:attachment_id>/open/', views.open_attachment, name='open_chat_attachment'),
    path('attachments/<int:attachment_id>/download/', views.download_attachment, name='download_chat_attachment'),
    path('start/<int:performer_id>/', views.start_chat_with_performer, name='start_chat_with_performer'),
    path('start/user/<int:user_id>/', views.start_chat_with_user, name='start_chat_with_user'),
]

from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_list, name='chat_list'),
    path('<int:room_id>/', views.chat_room, name='chat_room'),
    path('<int:room_id>/send/', views.send_message, name='send_message'),
    path('start/<int:performer_id>/', views.start_chat_with_performer, name='start_chat_with_performer'),
]
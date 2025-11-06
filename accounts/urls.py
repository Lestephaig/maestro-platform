from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    path('profile/view/', views.profile_view, name='profile_view'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('profile/media/', views.manage_media, name='manage_media'),
    path('profile/photo/add/', views.add_photo, name='add_photo'),
    path('profile/photo/<int:photo_id>/delete/', views.delete_photo, name='delete_photo'),
    path('profile/video/add/', views.add_video, name='add_video'),
    path('profile/video/<int:video_id>/delete/', views.delete_video, name='delete_video'),
    path('client/<int:user_id>/', views.client_public_profile, name='client_public_profile'),
]
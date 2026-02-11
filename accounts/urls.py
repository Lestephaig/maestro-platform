from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('verify-email/<uidb64>/<token>/', views.verify_email, name='verify_email'),
    path('email-verification-sent/', views.email_verification_sent, name='email_verification_sent'),
    path('email-verification-resend/', views.resend_verification_email, name='email_verification_resend'),
    path('venues/', views.venues_list, name='venues_list'),
    path('agents/', views.agents_list, name='agents_list'),
    path('profile/', views.profile, name='profile'),
    path('profile/view/', views.profile_view, name='profile_view'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('profile/media/', views.manage_media, name='manage_media'),
    path('profile/photo/add/', views.add_photo, name='add_photo'),
    path('profile/photo/<int:photo_id>/delete/', views.delete_photo, name='delete_photo'),
    path('profile/video/add/', views.add_video, name='add_video'),
    path('profile/video/<int:video_id>/delete/', views.delete_video, name='delete_video'),
    path('admin/users/<int:user_id>/delete/', views.admin_delete_user, name='admin_delete_user'),
    path('client/<int:user_id>/', views.client_public_profile, name='client_public_profile'),
    path('agent/<int:user_id>/', views.agent_public_profile, name='agent_public_profile'),
]
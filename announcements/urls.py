from django.urls import path
from . import views

app_name = 'announcements'

urlpatterns = [
    path('', views.announcement_list, name='list'),
    path('create/', views.announcement_create, name='create'),
    path('<int:announcement_id>/', views.announcement_detail, name='detail'),
    path('<int:announcement_id>/edit/', views.announcement_edit, name='edit'),
    path('<int:announcement_id>/complete/', views.announcement_complete, name='complete'),
    path('<int:announcement_id>/responses/', views.announcement_responses, name='responses'),
    path('my/', views.my_announcements, name='my_announcements'),
]


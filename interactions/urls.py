from django.urls import path

from . import views

app_name = 'interactions'

urlpatterns = [
    path('', views.interaction_list, name='list'),
    path('my/', views.my_projects, name='my_projects'),
    path('new/', views.interaction_create, name='create'),
    path('<int:pk>/', views.interaction_detail, name='detail'),
    path('<int:pk>/edit/', views.interaction_update, name='update'),
    path('<int:pk>/cancel/', views.cancel_project, name='cancel_project'),
    path('<int:pk>/complete/', views.complete_project, name='complete_project'),
    path('<int:pk>/reports/add/', views.interaction_add_report, name='add_report'),
    path('participations/<int:pk>/<str:decision>/', views.participant_decision, name='participant_decision'),
    path('participations/<int:pk>/completion/<str:decision>/', views.participant_completion_decision, name='participant_completion_decision'),
]


from django.urls import path
from . import views

app_name = 'performers'

urlpatterns = [
    path('specialists/', views.specialists_list, name='specialists'),
    path('performer/<int:performer_id>/', views.performer_detail, name='performer_detail'),
    path('api/performer/<int:performer_id>/calendar/', views.get_calendar_data, name='get_calendar_data'),
    path('api/performer/<int:performer_id>/availability/', views.update_availability, name='update_availability'),
    path('api/performer/<int:performer_id>/calendar-mode/', views.update_calendar_mode, name='update_calendar_mode'),
    
    # Repertoire management
    path('api/repertoire/add/', views.add_repertoire_item, name='add_repertoire_item'),
    path('api/repertoire/<int:item_id>/update/', views.update_repertoire_item, name='update_repertoire_item'),
    path('api/repertoire/<int:item_id>/delete/', views.delete_repertoire_item, name='delete_repertoire_item'),
    path('api/repertoire/reorder/', views.reorder_repertoire, name='reorder_repertoire'),
    
    # Autocomplete APIs
    path('api/autocomplete/composers/', views.autocomplete_composers, name='autocomplete_composers'),
    path('api/autocomplete/works/', views.autocomplete_works, name='autocomplete_works'),
]

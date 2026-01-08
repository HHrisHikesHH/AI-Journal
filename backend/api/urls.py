from django.urls import path
from . import views

urlpatterns = [
    path('entry/', views.create_entry, name='create_entry'),
    path('entries/', views.get_entries, name='get_entries'),
    path('query/', views.query, name='query'),
    path('rebuild_index/', views.rebuild_index, name='rebuild_index'),
    path('config/', views.get_config, name='get_config'),
    path('insight/on_open/', views.insight_on_open, name='insight_on_open'),
    path('search/', views.search, name='search'),
    path('export/', views.export_entries, name='export_entries'),
    path('action/', views.create_action_item, name='create_action'),
    path('actions/', views.get_action_items, name='get_actions'),
    path('action/<str:action_id>/', views.update_action_item, name='update_action'),
    path('action/<str:action_id>/delete/', views.delete_action_item, name='delete_action'),
]


from django.urls import path
from . import views

urlpatterns = [
    path('entry/', views.create_entry, name='create_entry'),
    path('entries/', views.get_entries, name='get_entries'),
    path('query/', views.query, name='query'),
    path('rebuild_index/', views.rebuild_index, name='rebuild_index'),
    path('config/', views.get_config, name='get_config'),
]


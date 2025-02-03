from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.spotify_login, name='spotify_login'),
    path('callback/', views.spotify_callback, name='spotify_callback'),
    path('status/', views.spotify_realtime_status, name='spotify_realtime_status'),
    path('index/', views.index, name='index'),
    # New party URL patterns:
    path('start_party/', views.start_party, name='start_party'),
    path('join_party/', views.join_party, name='join_party'),
    # New party management URL patterns:
    path('quit_party/', views.quit_party, name='quit_party'),
    path('delete_party/', views.delete_party, name='delete_party'),  # ensure this pattern exists
]
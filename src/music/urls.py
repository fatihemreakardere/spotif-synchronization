from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.spotify_login, name='spotify_login'),
    path('callback/', views.spotify_callback, name='spotify_callback'),
    path('status/', views.spotify_realtime_status, name='spotify_realtime_status'),
    path('index/', views.index, name='index'),
]
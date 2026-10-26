from django.urls import path

from . import views

app_name = "songs"

urlpatterns = [
    path("", views.song_list, name="song_list"),
    path("new/", views.song_create, name="song_create"),
    path("<int:pk>/", views.song_detail, name="song_detail"),
    path("<int:pk>/print/", views.song_print, name="song_print"),
    path("<int:pk>/edit/", views.song_update, name="song_update"),
    path("<int:pk>/delete/", views.song_delete, name="song_delete"),
    path("<int:pk>/rate/", views.song_rate, name="song_rate"),
]

from django.urls import path

from .views import SignupView, SongTroveLoginView, SongTroveLogoutView

urlpatterns = [
    path("signup/", SignupView.as_view(), name="signup"),
    path("login/", SongTroveLoginView.as_view(), name="login"),
    path("logout/", SongTroveLogoutView.as_view(), name="logout"),
]

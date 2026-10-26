from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView

from .forms import SignupForm


class SignupView(CreateView):
    """Create an account, then log the new user straight in."""

    form_class = SignupForm
    template_name = "accounts/signup.html"
    success_url = reverse_lazy("songs:song_list")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(self.success_url)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(self.request, "Welcome to SongTrove. Your library is ready.")
        return response


class SongTroveLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True


class SongTroveLogoutView(LogoutView):
    next_page = reverse_lazy("home")

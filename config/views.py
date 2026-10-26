from django.shortcuts import redirect, render


def home(request):
    """Landing page for visitors; a shortcut into the library once signed in."""
    if request.user.is_authenticated:
        return redirect("songs:song_list")
    return render(request, "home.html")

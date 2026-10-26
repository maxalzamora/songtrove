from django.db import DatabaseError, connection
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache


def home(request):
    """Landing page for visitors; a shortcut into the library once signed in."""
    if request.user.is_authenticated:
        return redirect("songs:song_list")
    return render(request, "home.html")


@never_cache
def healthz(request):
    """Liveness probe for an uptime monitor: is the app, and its database, up?"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return HttpResponse("database unavailable", status=503, content_type="text/plain")
    return HttpResponse("ok", content_type="text/plain")

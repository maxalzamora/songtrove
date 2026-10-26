from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def song_list(request):
    """The signed-in user's library."""
    songs = request.user.songs.prefetch_related("tags")
    return render(request, "songs/song_list.html", {"songs": songs})

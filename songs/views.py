from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import SongForm
from .models import Song


@login_required
def song_list(request):
    """The signed-in user's library."""
    songs = request.user.songs.prefetch_related("tags")
    return render(request, "songs/song_list.html", {"songs": songs})


@login_required
def song_detail(request, pk):
    song = get_object_or_404(request.user.songs.prefetch_related("tags"), pk=pk)
    return render(request, "songs/song_detail.html", {"song": song})


@login_required
def song_create(request):
    form = SongForm(request.POST or None, owner=request.user)

    if request.method == "POST" and form.is_valid():
        song = form.save()
        messages.success(request, f"“{song.title}” added to your library.")
        return redirect(song)

    return render(request, "songs/song_form.html", {"form": form, "song": None})


@login_required
def song_update(request, pk):
    song = get_object_or_404(request.user.songs, pk=pk)
    form = SongForm(request.POST or None, instance=song, owner=request.user)

    if request.method == "POST" and form.is_valid():
        song = form.save()
        messages.success(request, f"“{song.title}” saved.")
        return redirect(song)

    return render(request, "songs/song_form.html", {"form": form, "song": song})


@login_required
def song_delete(request, pk):
    song = get_object_or_404(request.user.songs, pk=pk)

    if request.method == "POST":
        title = song.title
        song.delete()
        messages.success(request, f"“{title}” deleted.")
        return redirect("songs:song_list")

    return render(request, "songs/song_confirm_delete.html", {"song": song})

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

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


@login_required
@require_POST
def song_rate(request, pk):
    """Set or clear the one-to-five performance rating."""
    song = get_object_or_404(request.user.songs, pk=pk)
    raw = request.POST.get("rating", "").strip()

    if not raw:
        song.rating = None
    else:
        try:
            rating = int(raw)
        except ValueError:
            return HttpResponseBadRequest("Rating must be a number from 1 to 5.")
        if not 1 <= rating <= 5:
            return HttpResponseBadRequest("Rating must be between 1 and 5.")
        song.rating = rating

    song.save(update_fields=["rating", "updated_at"])
    messages.success(request, "Rating saved." if song.rating else "Rating cleared.")
    return redirect(song)

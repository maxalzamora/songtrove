"""Core domain models: a song, its chord sheet, and free-form tags."""

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse

from .chords.theory import KEY_CHOICES


class Tag(models.Model):
    """A label a user can attach to their own songs."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tags",
    )
    name = models.CharField(max_length=50)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "name"],
                name="unique_tag_name_per_owner",
            )
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        self.name = self.name.strip()
        return super().save(*args, **kwargs)


class Song(models.Model):
    """A chord sheet plus the details a player needs at the stand."""

    class Status(models.TextChoices):
        IDEA = "idea", "Idea"
        LEARNING = "learning", "Learning"
        PRACTICING = "practicing", "Practicing"
        GIG_READY = "gig_ready", "Gig ready"

    class Mode(models.TextChoices):
        MAJOR = "major", "Major"
        MINOR = "minor", "Minor"

    class SheetFormat(models.TextChoices):
        CHORDPRO = "chordpro", "ChordPro"
        PLAIN = "plain", "Plain text"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="songs",
    )

    title = models.CharField(max_length=200)
    artist = models.CharField(max_length=200, blank=True)

    song_key = models.CharField(max_length=2, choices=KEY_CHOICES, blank=True)
    mode = models.CharField(max_length=5, choices=Mode.choices, default=Mode.MAJOR)
    capo = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(12)],
        help_text="Fret the capo sits on. 0 means no capo.",
    )

    rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="How well you can perform it, 1 to 5 stars.",
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.LEARNING,
    )

    tempo = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Beats per minute.",
    )
    time_signature = models.CharField(max_length=8, blank=True, default="4/4")
    tuning = models.CharField(max_length=40, blank=True, default="Standard")

    sheet_format = models.CharField(
        max_length=16,
        choices=SheetFormat.choices,
        default=SheetFormat.CHORDPRO,
    )
    sheet_body = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    source_url = models.URLField(blank=True)

    tags = models.ManyToManyField(Tag, blank=True, related_name="songs")

    last_practiced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title", "artist"]
        indexes = [
            models.Index(fields=["owner", "status"], name="song_owner_status_idx"),
            models.Index(fields=["owner", "artist"], name="song_owner_artist_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.title} — {self.artist}" if self.artist else self.title

    def get_absolute_url(self) -> str:
        return reverse("songs:song_detail", args=[self.pk])

    @property
    def display_key(self) -> str:
        """Key as a player would write it: ``Em``, ``Bb``, or empty."""
        if not self.song_key:
            return ""
        return f"{self.song_key}m" if self.mode == self.Mode.MINOR else self.song_key

    @property
    def is_chordpro(self) -> bool:
        return self.sheet_format == self.SheetFormat.CHORDPRO

    @property
    def rating_stars(self) -> str:
        """Filled and empty stars for display, or empty when unrated."""
        if not self.rating:
            return ""
        return "★" * self.rating + "☆" * (5 - self.rating)

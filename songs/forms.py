from django import forms
from django.core.exceptions import ValidationError

from .chords.theory import KEY_CHOICES
from .models import Song, Tag

MAX_TAGS = 12


class SongForm(forms.ModelForm):
    """Create or edit a song, including its comma-separated tags."""

    tags_input = forms.CharField(
        required=False,
        label="Tags",
        help_text="Comma separated, e.g. folk, campfire, 3/4",
    )

    class Meta:
        model = Song
        fields = [
            "title",
            "artist",
            "status",
            "song_key",
            "mode",
            "capo",
            "tempo",
            "time_signature",
            "tuning",
            "sheet_format",
            "sheet_body",
            "source_url",
            "notes",
        ]
        widgets = {
            "capo": forms.NumberInput(attrs={"min": 0, "max": 12, "step": 1}),
            "tempo": forms.NumberInput(attrs={"min": 20, "max": 320, "step": 1, "placeholder": "120"}),
            "sheet_body": forms.Textarea(
                attrs={
                    "rows": 18,
                    "spellcheck": "false",
                    "class": "mono",
                    "placeholder": "[G]Amazing [C]grace, how [G]sweet the [D]sound",
                }
            ),
            "notes": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, owner, **kwargs):
        self.owner = owner
        super().__init__(*args, **kwargs)

        if not self.instance.pk:
            self.instance.owner = owner

        self.fields["song_key"].choices = (("", "—"), *KEY_CHOICES)
        self.fields["song_key"].label = "Key, as written"
        self.fields["song_key"].help_text = (
            "The key of the chords on the sheet, before the capo."
        )
        self.fields["sheet_format"].help_text = (
            "ChordPro lets the sheet be transposed; plain text is shown as typed."
        )

        if self.instance.pk:
            self.fields["tags_input"].initial = ", ".join(
                tag.name for tag in self.instance.tags.all()
            )

    def clean_tags_input(self) -> list[str]:
        raw = self.cleaned_data.get("tags_input", "")
        names: list[str] = []
        seen: set[str] = set()

        for piece in raw.split(","):
            name = " ".join(piece.split())
            if not name:
                continue
            if len(name) > Tag._meta.get_field("name").max_length:
                raise ValidationError(f"Tags must be {Tag._meta.get_field('name').max_length} characters or fewer.")
            if name.lower() in seen:
                continue
            seen.add(name.lower())
            names.append(name)

        if len(names) > MAX_TAGS:
            raise ValidationError(f"Please use {MAX_TAGS} tags or fewer.")

        return names

    def save(self, commit: bool = True) -> Song:
        song = super().save(commit=commit)
        if commit:
            song.tags.set(self._resolve_tags())
        return song

    def _resolve_tags(self) -> list[Tag]:
        """Reuse the owner's existing tags, matching case-insensitively."""
        existing = {tag.name.lower(): tag for tag in Tag.objects.filter(owner=self.owner)}
        resolved: list[Tag] = []

        for name in self.cleaned_data.get("tags_input", []):
            tag = existing.get(name.lower())
            if tag is None:
                tag = Tag.objects.create(owner=self.owner, name=name)
                existing[name.lower()] = tag
            resolved.append(tag)

        return resolved

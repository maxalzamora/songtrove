"""Load the bundled public-domain songs into one account."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from songs.models import Song, Tag
from songs.seed_data import SONGS


class Command(BaseCommand):
    help = "Add the starter library of public-domain songs to one user's account."

    def add_arguments(self, parser):
        parser.add_argument(
            "--user",
            required=True,
            help="Username of the account that will own the seeded songs.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        username = options["user"]

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"No user named {username!r}. Create it first.") from None

        created = skipped = 0
        for entry in SONGS:
            fields = dict(entry)
            tag_names = fields.pop("tags", ())

            if Song.objects.filter(
                owner=user,
                title=fields["title"],
                artist=fields.get("artist", ""),
            ).exists():
                skipped += 1
                continue

            song = Song.objects.create(owner=user, **fields)
            song.tags.set(self._tags_for(user, tag_names))
            created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {created} song(s) for {username}; skipped {skipped} already there."
            )
        )

    @staticmethod
    def _tags_for(user, names) -> list[Tag]:
        """Reuse an existing tag regardless of how it is capitalised."""
        tags = []
        for name in names:
            tag = Tag.objects.filter(owner=user, name__iexact=name).first()
            if tag is None:
                tag = Tag.objects.create(owner=user, name=name)
            tags.append(tag)
        return tags

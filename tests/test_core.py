"""Tests for song storage, manual entry and chord-sheet rendering."""

from __future__ import annotations

import html
import io
import json
import os
import re
import sqlite3
import tempfile
import unittest
from pathlib import Path

from werkzeug.security import generate_password_hash

# Keep the module-level Flask app created by ``app.py`` away from real data.
_TEST_DB_DIR = tempfile.TemporaryDirectory()
os.environ["SONGBOOK_DB"] = str(Path(_TEST_DB_DIR.name) / "app.db")
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["SONGBOOK_USERNAME"] = "tester"
os.environ["SONGBOOK_PASSWORD_HASH"] = generate_password_hash("test-password")

import db
from app import create_app
from render import chord_sheet_html, merge_edited_text, plain_sheet_text, transpose_chord

TEST_USERNAME = "tester"
TEST_PASSWORD = "test-password"

CONTENT = """[Intro]
[ch]G[/ch] [ch]C[/ch]

[tab]      [ch]G[/ch]            [ch]C[/ch]
When you were here before[/tab]

[Verse 1] (softly)
[ch]Am[/ch] <this> & that
Capo 3
"""

LEGACY_SCHEMA = """
CREATE TABLE songs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT    NOT NULL,
    artist     TEXT    NOT NULL,
    tab_type   TEXT    NOT NULL DEFAULT '',
    content    TEXT    NOT NULL,
    song_key   TEXT    NOT NULL DEFAULT '',
    tuning     TEXT    NOT NULL DEFAULT '',
    capo       INTEGER NOT NULL DEFAULT 0,
    rating     INTEGER NOT NULL DEFAULT 0,
    created_at TEXT    NOT NULL,
    updated_at TEXT    NOT NULL
);
CREATE INDEX idx_songs_created ON songs (created_at DESC);
"""


def visible_text(fragment: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", fragment))


def log_in(client) -> None:
    response = client.post(
        "/login",
        data={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )
    if response.status_code != 302:
        raise AssertionError(f"login failed: {response.status_code}")


class RenderTests(unittest.TestCase):
    def test_preserves_every_visible_character(self):
        rendered = chord_sheet_html(CONTENT)
        expected = (
            CONTENT.replace("[tab]", "")
            .replace("[/tab]", "")
            .replace("[ch]", "")
            .replace("[/ch]", "")
        )
        self.assertEqual(visible_text(rendered), expected)

    def test_marks_chords(self):
        rendered = chord_sheet_html("[ch]C#m7[/ch]  hello")
        self.assertIn(
            '<span class="chord" data-chord="C#m7">C#m7</span>  hello', rendered
        )

    def test_detects_plain_chord_lines(self):
        rendered = chord_sheet_html("[Verse]\nG       D\nLyrics here")
        self.assertIn(
            '<span class="chord" data-chord="G">G</span>       '
            '<span class="chord" data-chord="D">D</span>',
            rendered,
        )
        self.assertIn("Lyrics here", rendered)

    def test_does_not_mark_chords_inside_lyrics(self):
        rendered = chord_sheet_html("Am I in the frame from your point of view?")
        self.assertNotIn('class="chord"', rendered)

    def test_plain_chord_detection_preserves_every_character(self):
        content = "G       D\nLyrics stay here"
        self.assertEqual(visible_text(chord_sheet_html(content)), content)

    def test_detects_chord_line_with_bars_and_repeat_count(self):
        rendered = chord_sheet_html("| G | D | (x2)")
        self.assertIn('<span class="chord" data-chord="G">G</span>', rendered)
        self.assertIn('<span class="chord" data-chord="D">D</span>', rendered)

    def test_detects_common_complex_chord_lines(self):
        rendered = chord_sheet_html("G7sus4   Cadd9   F#m7b5   C7(b9)")
        for chord in ("G7sus4", "Cadd9", "F#m7b5", "C7(b9)"):
            self.assertIn(f'data-chord="{chord}"', rendered)

    def test_transposes_chord_names_and_keeps_original_for_the_browser(self):
        rendered = chord_sheet_html("G   D/F#   Cmaj7", transpose=-2)
        self.assertIn('<span class="chord" data-chord="G">F</span>', rendered)
        self.assertIn('<span class="chord" data-chord="D/F#">C/E</span>', rendered)
        self.assertIn(
            '<span class="chord" data-chord="Cmaj7">Bbmaj7</span>', rendered
        )

    def test_transpose_chord_preserves_quality_and_slash_bass(self):
        self.assertEqual(transpose_chord("G", -3), "E")
        self.assertEqual(transpose_chord("Fadd9", -3), "Dadd9")
        self.assertEqual(transpose_chord("G/B", -3), "E/G#")
        self.assertEqual(transpose_chord("F#m7", -2), "Em7")
        self.assertEqual(transpose_chord("A", 1), "Bb")
        self.assertEqual(transpose_chord("E", -3), "C#")
        self.assertEqual(transpose_chord("C6/9", -2), "Bb6/9")
        self.assertEqual(transpose_chord("N.C.", -2), "N.C.")
        self.assertEqual(transpose_chord("G", -12), "G")

    def test_marks_sections(self):
        rendered = chord_sheet_html("[Verse 1] (softly)\nlyrics")
        self.assertIn(
            '<span class="sheet-section">[Verse 1] (softly)</span>', rendered
        )

    def test_escapes_third_party_html(self):
        rendered = chord_sheet_html("<script>alert('x')</script>\n[ch]<b>C</b>[/ch]")
        self.assertNotIn("<script>", rendered)
        self.assertNotIn("<b>", rendered)
        self.assertIn("&lt;script&gt;", rendered)
        self.assertIn("&lt;b&gt;C&lt;/b&gt;", rendered)

    def test_handles_windows_line_endings(self):
        self.assertEqual(chord_sheet_html("a\r\nb\rc"), "a\nb\nc")


class EditSheetTests(unittest.TestCase):
    def test_plain_text_matches_what_is_displayed(self):
        self.assertEqual(
            visible_text(chord_sheet_html(CONTENT)), plain_sheet_text(CONTENT)
        )

    def test_deleting_filler_keeps_chord_markup_on_remaining_lines(self):
        edited = """[Intro]
G C

[Verse 1] (softly)
Am <this> & that
Capo 3
"""
        merged = merge_edited_text(CONTENT, edited)

        self.assertNotIn("Filler", merged)
        self.assertIn("[ch]G[/ch]", merged)
        self.assertIn("[ch]Am[/ch]", merged)
        self.assertEqual(plain_sheet_text(merged), edited)

    def test_edited_lines_are_saved_as_plain_text(self):
        edited = CONTENT.replace("[ch]Am[/ch] <this> & that", "A5 <this> & that")
        merged = merge_edited_text(CONTENT, edited)

        self.assertIn("A5 <this> & that", merged)
        self.assertNotIn("[ch]A5[/ch]", merged)
        self.assertEqual(plain_sheet_text(merged), plain_sheet_text(edited))

    def test_unchanged_edit_round_trips_rendering(self):
        edited = plain_sheet_text(CONTENT)
        merged = merge_edited_text(CONTENT, edited)

        self.assertEqual(chord_sheet_html(merged), chord_sheet_html(CONTENT))

    def test_normalizes_windows_line_endings(self):
        merged = merge_edited_text("a\r\n[ch]C[/ch]\r\n", "a\nC\n")
        self.assertEqual(merged, "a\n[ch]C[/ch]\n")


class AuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.database = str(Path(self.tempdir.name) / "songbook.db")
        self.app = create_app(self.database)
        self.app.config.update(
            TESTING=True, WTF_CSRF_ENABLED=False, LOGIN_FAILURE_DELAY=0
        )
        self.client = self.app.test_client()

    def tearDown(self):
        self.tempdir.cleanup()

    def test_private_pages_redirect_to_login(self):
        for path in ("/", "/song/1", "/song/1/edit", "/songs/new", "/export", "/import"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 302)
            self.assertIn("/login", response.headers["Location"])

    def test_health_check_is_public(self):
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"ok": True})

    def test_wrong_password_is_rejected(self):
        response = self.client.post(
            "/login", data={"username": TEST_USERNAME, "password": "wrong"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Wrong username or password.", response.get_data(as_text=True))
        with self.client.session_transaction() as session:
            self.assertFalse(session.get("authenticated"))

    def test_login_and_logout(self):
        log_in(self.client)
        self.assertEqual(self.client.get("/").status_code, 200)

        response = self.client.post("/logout")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/login"))
        self.assertEqual(self.client.get("/").status_code, 302)

    def test_csrf_token_is_required_and_accepted(self):
        self.app.config["WTF_CSRF_ENABLED"] = True
        missing_token = self.client.post(
            "/login",
            data={"username": TEST_USERNAME, "password": TEST_PASSWORD},
        )
        self.assertEqual(missing_token.status_code, 302)
        self.assertIn("/login", missing_token.headers["Location"])
        with self.client.session_transaction() as session:
            self.assertFalse(session.get("authenticated"))

        page = self.client.get("/login").get_data(as_text=True)
        token = re.search(
            r'name="csrf_token" value="([^"]+)"', page
        ).group(1)
        response = self.client.post(
            "/login",
            data={
                "username": TEST_USERNAME,
                "password": TEST_PASSWORD,
                "csrf_token": token,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/"))

    def test_security_headers_are_present(self):
        response = self.client.get("/login")
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertIn("noindex", response.headers["X-Robots-Tag"])

    def test_login_rejects_external_next_url(self):
        response = self.client.post(
            "/login?next=https://example.com",
            data={"username": TEST_USERNAME, "password": TEST_PASSWORD},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/"))


class ManualSongTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.database = str(Path(self.tempdir.name) / "songbook.db")
        self.app = create_app(self.database)
        self.app.config.update(
            TESTING=True, WTF_CSRF_ENABLED=False, LOGIN_FAILURE_DELAY=0
        )
        self.client = self.app.test_client()
        log_in(self.client)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_new_song_page_has_manual_fields_with_standard_tuning(self):
        response = self.client.get("/songs/new")

        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        self.assertIn("Add a song", page)
        self.assertIn('name="title"', page)
        self.assertIn('name="artist"', page)
        self.assertIn('name="content"', page)
        self.assertIn('name="tuning"', page)
        self.assertIn('value="E A D G B E"', page)
        self.assertIn('name="capo"', page)
        self.assertIn('name="rating"', page)
        self.assertNotIn('name="tab_type"', page)
        self.assertNotIn('name="song_key"', page)

    def test_adds_song_with_all_attributes(self):
        response = self.client.post(
            "/songs/new",
            data={
                "title": "Manual Song",
                "artist": "A Player",
                "tuning": "Drop D",
                "capo": "3",
                "rating": "4",
                "content": "[Verse]\nG   D\nLyrics here",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/song/1"))

        with self.app.app_context():
            song = db.get_song(1)
            self.assertIsNotNone(song)
            self.assertEqual(song["title"], "Manual Song")
            self.assertEqual(song["artist"], "A Player")
            self.assertEqual(song["tuning"], "Drop D")
            self.assertEqual(song["capo"], 3)
            self.assertEqual(song["rating"], 4)
            self.assertEqual(song["content"], "[Verse]\nG   D\nLyrics here")
            self.assertEqual(set(song.keys()), db.TARGET_COLUMNS)

        page = self.client.get("/song/1").get_data(as_text=True)
        self.assertIn("Manual Song", page)
        self.assertIn("Lyrics here", page)
        self.assertIn("Edit song", page)
        self.assertIn('href="/song/1/edit"', page)

    def test_blank_tuning_defaults_to_standard(self):
        self.client.post(
            "/songs/new",
            data={
                "title": "Standard Song",
                "artist": "A Player",
                "tuning": " ",
                "content": "G",
            },
        )

        with self.app.app_context():
            song = db.get_song(1)
            self.assertEqual(song["tuning"], db.DEFAULT_TUNING)

    def test_requires_title_artist_and_content(self):
        response = self.client.post(
            "/songs/new",
            data={
                "title": " ",
                "artist": "",
                "content": "\n  \n",
            },
        )

        self.assertEqual(response.status_code, 400)
        page = response.get_data(as_text=True)
        self.assertIn("Add a title.", page)
        self.assertIn("Add an artist.", page)
        self.assertIn("Add the chords or lyrics.", page)

        with self.app.app_context():
            self.assertEqual(db.count_songs(), 0)

    def test_clamps_capo_and_rating(self):
        self.client.post(
            "/songs/new",
            data={
                "title": "Loud Song",
                "artist": "A Player",
                "capo": "99",
                "rating": "-2",
                "content": "G",
            },
        )

        with self.app.app_context():
            song = db.get_song(1)
            self.assertEqual(song["capo"], 12)
            self.assertEqual(song["rating"], 0)

    def test_index_uses_a_compact_song_list(self):
        self.client.post(
            "/songs/new",
            data={
                "title": "List Song",
                "artist": "A Player",
                "capo": "2",
                "content": "G",
            },
        )
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        self.assertIn('class="song-list"', page)
        self.assertIn('class="song-list-head"', page)
        self.assertIn('class="song-row"', page)
        self.assertIn("List Song", page)
        self.assertIn("A Player", page)
        self.assertIn(">Song</span>", page)
        self.assertIn(">Artist</span>", page)
        self.assertIn(">Capo</span>", page)
        self.assertIn(">Tuning</span>", page)
        self.assertIn(">Rating</span>", page)
        self.assertIn('class="song-cell-value">2</span>', page)
        self.assertIn("Standard", page)
        self.assertIn('href="/songs/new"', page)
        self.assertIn("Add a song", page)

    def test_export_has_only_current_fields(self):
        self.client.post(
            "/songs/new",
            data={
                "title": "Export Song",
                "artist": "A Player",
                "content": "G",
            },
        )

        payload = json.loads(self.client.get("/export").get_data(as_text=True))
        self.assertEqual(len(payload["songs"]), 1)
        self.assertEqual(set(payload["songs"][0]), db.TARGET_COLUMNS)

    def test_import_adds_songs_from_an_export(self):
        exported = {
            "songs": [
                {
                    "title": "Imported Song",
                    "artist": "Imported Artist",
                    "content": "[Verse]\nG\nWords",
                    "tuning": "Drop D",
                    "capo": 2,
                    "rating": 5,
                    "id": 99,
                },
                {
                    "title": "Standard Song",
                    "artist": "Another Artist",
                    "content": "C",
                    "tuning": "",
                    "capo": 0,
                    "rating": 0,
                },
            ]
        }
        response = self.client.post(
            "/import",
            data={
                "songbook": (
                    io.BytesIO(json.dumps(exported).encode("utf-8")),
                    "songbook.json",
                )
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            self.assertEqual(db.count_songs(), 2)
            song = db.get_song(1)
            self.assertEqual(song["title"], "Imported Song")
            self.assertEqual(song["artist"], "Imported Artist")
            self.assertEqual(song["tuning"], "Drop D")
            self.assertEqual(song["capo"], 2)
            self.assertEqual(song["rating"], 5)
            self.assertEqual(song["content"], "[Verse]\nG\nWords")
            self.assertEqual(db.get_song(2)["tuning"], db.DEFAULT_TUNING)

    def test_import_rejects_invalid_json_without_writing(self):
        response = self.client.post(
            "/import",
            data={
                "songbook": (io.BytesIO(b"{not json"), "songbook.json"),
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("not valid JSON", response.get_data(as_text=True))
        with self.app.app_context():
            self.assertEqual(db.count_songs(), 0)

    def test_import_rejects_partial_invalid_file_without_writing(self):
        exported = {
            "songs": [
                {
                    "title": "Good Song",
                    "artist": "Artist",
                    "content": "G",
                },
                {
                    "title": "",
                    "artist": "Artist",
                    "content": "C",
                },
            ]
        }
        response = self.client.post(
            "/import",
            data={
                "songbook": (
                    io.BytesIO(json.dumps(exported).encode("utf-8")),
                    "songbook.json",
                )
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Song 2 needs a title", response.get_data(as_text=True))
        with self.app.app_context():
            self.assertEqual(db.count_songs(), 0)

    def test_import_page_explains_the_backup_format(self):
        response = self.client.get("/import")

        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        self.assertIn('type="file"', page)
        self.assertIn('enctype="multipart/form-data"', page)
        self.assertIn("Export songbook", page)


class EditSongTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.database = str(Path(self.tempdir.name) / "songbook.db")
        self.app = create_app(self.database)
        self.app.config.update(
            TESTING=True, WTF_CSRF_ENABLED=False, LOGIN_FAILURE_DELAY=0
        )
        self.client = self.app.test_client()
        log_in(self.client)
        with self.app.app_context():
            self.song_id = db.add_manual_song(
                title="Original Song",
                artist="Original Artist",
                tuning="E A D G B E",
                capo=1,
                rating=3,
                content="[Verse]\n[ch]G[/ch]\nOld words",
            )

    def tearDown(self):
        self.tempdir.cleanup()

    def test_edit_page_prefills_every_field(self):
        response = self.client.get(f"/song/{self.song_id}/edit")

        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        self.assertIn('name="title"', page)
        self.assertIn('value="Original Song"', page)
        self.assertIn('name="artist"', page)
        self.assertIn('value="Original Artist"', page)
        self.assertIn('name="tuning"', page)
        self.assertIn('value="E A D G B E"', page)
        self.assertIn('name="capo"', page)
        self.assertIn('value="1"', page)
        self.assertIn('name="rating"', page)
        self.assertIn("<option value=\"3\" selected>3 stars</option>", page)
        self.assertIn("G\nOld words", page)
        self.assertNotIn("[ch]G[/ch]", page)

    def test_edit_page_updates_all_fields_and_merges_sheet(self):
        response = self.client.post(
            f"/song/{self.song_id}/edit",
            data={
                "title": "Renamed Song",
                "artist": "New Artist",
                "tuning": "Drop D",
                "capo": "2",
                "rating": "5",
                "content": "[Verse]\nG\nNew words",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            response.headers["Location"].endswith(f"/song/{self.song_id}")
        )
        with self.app.app_context():
            song = db.get_song(self.song_id)
            self.assertEqual(song["title"], "Renamed Song")
            self.assertEqual(song["artist"], "New Artist")
            self.assertEqual(song["tuning"], "Drop D")
            self.assertEqual(song["capo"], 2)
            self.assertEqual(song["rating"], 5)
            self.assertEqual(song["content"], "[Verse]\n[ch]G[/ch]\nNew words")

        page = self.client.get(f"/song/{self.song_id}").get_data(as_text=True)
        self.assertIn("Renamed Song", page)
        self.assertIn("New Artist", page)
        self.assertIn("New words", page)
        self.assertIn("Drop D", page)

    def test_edit_defaults_blank_tuning_and_rejects_empty_fields(self):
        response = self.client.post(
            f"/song/{self.song_id}/edit",
            data={
                "title": " ",
                "artist": "",
                "tuning": " ",
                "capo": "4",
                "rating": "5",
                "content": "   ",
            },
        )

        self.assertEqual(response.status_code, 400)
        page = response.get_data(as_text=True)
        self.assertIn("Add a title.", page)
        self.assertIn("Add an artist.", page)
        self.assertIn("Add the chords or lyrics.", page)
        with self.app.app_context():
            song = db.get_song(self.song_id)
            self.assertEqual(song["title"], "Original Song")
            self.assertEqual(song["artist"], "Original Artist")
            self.assertEqual(song["capo"], 1)
            self.assertEqual(song["rating"], 3)

        response = self.client.post(
            f"/song/{self.song_id}/edit",
            data={
                "title": "Original Song",
                "artist": "Original Artist",
                "tuning": "",
                "capo": "4",
                "rating": "5",
                "content": "G",
            },
        )
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            song = db.get_song(self.song_id)
            self.assertEqual(song["tuning"], db.DEFAULT_TUNING)


class LegacyDatabaseMigrationTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.database = str(Path(self.tempdir.name) / "legacy.db")
        connection = sqlite3.connect(self.database)
        connection.executescript(LEGACY_SCHEMA)
        connection.executemany(
            """INSERT INTO songs
                   (title, artist, tab_type, content, song_key, tuning,
                    capo, rating, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    "Old Song",
                    "Old Artist",
                    "Tab",
                    "[Verse]\nG\nLyrics",
                    "G",
                    "",
                    2,
                    5,
                    "2025-01-02T03:04:05Z",
                    "2025-02-03T04:05:06Z",
                ),
                (
                    "Custom Tuning",
                    "Another Artist",
                    "Chords",
                    "D",
                    "D",
                    "Drop D",
                    0,
                    0,
                    "2025-03-04T05:06:07Z",
                    "2025-03-04T05:06:07Z",
                ),
            ],
        )
        connection.commit()
        connection.close()

    def tearDown(self):
        self.tempdir.cleanup()

    def test_migrates_previous_schema_and_keeps_song_data(self):
        app = create_app(self.database)
        app.config.update(TESTING=True)

        with app.app_context():
            song = db.get_song(1)
            self.assertIsNotNone(song)
            self.assertEqual(song["title"], "Old Song")
            self.assertEqual(song["artist"], "Old Artist")
            self.assertEqual(song["content"], "[Verse]\nG\nLyrics")
            self.assertEqual(song["tuning"], db.DEFAULT_TUNING)
            self.assertEqual(song["capo"], 2)
            self.assertEqual(song["rating"], 5)
            self.assertEqual(set(song.keys()), db.TARGET_COLUMNS)

            custom = db.get_song(2)
            self.assertEqual(custom["tuning"], "Drop D")

            new_id = db.add_manual_song(
                title="New Song", artist="New Artist", content="C"
            )
            self.assertEqual(new_id, 3)
            self.assertEqual(db.get_song(new_id)["tuning"], db.DEFAULT_TUNING)

        # Running the initializer again must leave the migrated data alone.
        create_app(self.database)
        with app.app_context():
            self.assertEqual(db.count_songs(), 3)

    def test_blank_tuning_is_filled_on_current_schema(self):
        app = create_app(self.database)
        with app.app_context():
            database = db.get_db()
            database.execute("UPDATE songs SET tuning = '' WHERE id = 1")
            database.commit()

        create_app(self.database)
        with app.app_context():
            self.assertEqual(db.get_song(1)["tuning"], db.DEFAULT_TUNING)


if __name__ == "__main__":
    unittest.main()


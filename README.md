# Songtrove

A self-hosted chord and lyric library for guitar. Each account gets a private
library: add a song by hand — title, artist, tuning, capo, notes, source link,
tags and the full chord/lyric sheet — and keep it in a local SQLite database.
Each song gets a 1–5 star performance rating and a capo setting that transposes
the displayed chord names.

Repository: <https://github.com/maxalzamora/songtrove>

The chord sheet is rendered in a monospace font with all spacing preserved, so
chords stay exactly above the syllables they belong to. The source text is
highlighted without changing a character position; capo transposition then
replaces only the chord names.

The app never fetches or scrapes another website. Everything you add is entered
on the **Add song** page and stored locally.

## Features

- Manual song entry with title, artist, tuning, capo, performance rating, optional
  notes, a source URL and tags, plus the chord/lyric text. Standard tuning
  (`E A D G B E`) is used when no other tuning is entered.
- A compact song list makes a large library quick to scan, with title, artist,
  tags, capo, tuning and rating visible at a glance.
- Plain-text chord sheets are kept in a fixed-width layout. Chord-only lines that
  you paste or type are detected and highlighted automatically, while lyrics stay
  plain.
- Capo and 1–5 star performance rating save automatically, with a working
  fallback when JavaScript is off.
- The displayed chord names transpose down by the capo amount, so they are the
  shapes to play while the song keeps its original pitch. The sheet updates
  immediately on the page.
- An **Edit song** page for changing the title, artist, tuning, capo, rating,
  notes, source URL, tags and chord sheet in one place. Deleting whole lines
  removes filler, author notes or unwanted sections.
- Search by title, artist, notes or tags, then narrow the list by tag, rating or
  tuning. Sort by recently added, title, artist or rating.
- Stored locally in SQLite and available offline.
- Password-protected access with CSRF protection, so the library can be
  deployed publicly without exposing it.
- Multiple accounts with private libraries. The first admin is created from the
  environment on a fresh database; that admin can add members or other admins,
  reset passwords, disable accounts and change roles. Usernames are unique
  regardless of case, and password changes sign out that account's other
  sessions.
- A personal **Account** page for changing your own password.
- JSON export of the signed-in account's library, plus an authenticated import
  page for restoring an export into that account.
- Responsive dark UI and a print stylesheet for paper chord sheets.
- **Fit to screen** reading view: strips the page down to the chord sheet and
  an **Exit fit** control, splits the song into as many columns as the window
  allows, and scales the monospace text so the whole song is visible at once.
  Columns are packed at section markers such as `[Verse]`, `[Chorus]`,
  `[Bridge]`, `Verse 1:` and `C1:`, so a section is not cut between columns.
  Press **Esc** or click **Exit fit** to leave. The fit-view choice is
  remembered in the browser. For very long songs that cannot fit even at the
  8px minimum, the sheet scrolls inside the reading view instead of clipping
  text; columns still break on section markers where the song has them.

## Run it

Requires Python 3.10+, Flask and Flask-WTF.

```bash
git clone https://github.com/maxalzamora/songtrove.git
cd songtrove
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python3 manage.py set-password
python3 app.py
```

`manage.py set-password` asks for a password and writes a hash to `.env`; the
plain password is never stored. On the first start, the app creates an admin
account from `SONGTROVE_USERNAME` and that hash. Then open
<http://127.0.0.1:5000> and log in. The default username is `songtrove`; change
`SONGTROVE_USERNAME` in `.env` before the first start if you want a different
name.

The first start also gives any songs already in the database to that admin. Add
more accounts from **Users** in the header while signed in as an admin. Members
see only their own songs; the admin account screens manage users but do not
expose other members' libraries.

If you already have a `.env`, the app reads it automatically. Those bootstrap
values are only used when the database has no accounts yet. Change your own
password from **Account** in the header. As an admin, you can reset another
account's password from **Users**. If you are locked out, run:

```bash
python3 manage.py list-users
python3 manage.py reset-password USERNAME
```

`manage.py create-user USERNAME --role member` and the corresponding `admin`
role can also create accounts from the command line.

The server binds to `127.0.0.1` by default, so it is only reachable from the
same machine. To use it from another device on your network:

```bash
HOST=0.0.0.0 PORT=5000 python3 app.py
```

The app now has its own login, but binding to `0.0.0.0` still exposes it to
everyone on that network. For a public deployment, use HTTPS and the production
setup in [DEPLOYMENT.md](DEPLOYMENT.md).

## Configuration

| Variable                  | Default                  | Purpose                                      |
| ------------------------- | ------------------------ | -------------------------------------------- |
| `HOST`                    | `127.0.0.1`              | Address the dev server binds to              |
| `PORT`                    | `5000`                   | Port                                         |
| `SONGTROVE_DB`             | `data/songtrove.db`       | SQLite database file                         |
| `SECRET_KEY`              | generated in `data/`     | Flask session signing key                    |
| `SONGTROVE_USERNAME`       | `songtrove`               | First admin username on an empty database     |
| `SONGTROVE_PASSWORD_HASH`  | required on first start   | First admin password hash                     |
| `SONGTROVE_SECURE_COOKIES` | `0`                      | Set to `1` when serving over HTTPS           |
| `FLASK_DEBUG`             | `0`                      | Set to `1` for debug/reload                  |

## Data and backup

Everything lives in `data/songtrove.db`, including all accounts and their songs.
Copy that file to back up the whole installation, or use **Export songs** to
download a JSON snapshot of the signed-in account's library, then restore it
through **Import songs**. `data/` is ignored by git so personal data is not
committed by accident.

The database initializer upgrades older library databases in place. Existing
songs, capo settings, ratings and IDs are preserved; new notes, source links and
tags start empty. On the first multi-account start, the new `users` table is
created and existing songs are assigned to the first admin.

## Deployment

`DEPLOYMENT.md` covers the GitHub workflow, a free PythonAnywhere deployment
that keeps SQLite on a persistent disk, Render deployment with a persistent
disk, and a VPS setup using Gunicorn, systemd and Caddy. `render.yaml` and
`Procfile` are ready for a host that builds from GitHub. Never commit `.env` or
the `data/` folder.

## How it works

- `render.py` turns `[ch]G[/ch]` into a chord span, finds chord-only lines in
  plain-text sheets, drops `[tab]` wrapper tags, and escapes everything else. It
  transposes chord names for the current capo and keeps each original name in a
  `data-chord` attribute so the browser can update them live. The output is
  placed in a `<pre>` with `white-space: pre`, which is what keeps the layout
  fixed. It also creates the plain text for the editor and merges edits back
  line by line, so unchanged chord lines keep their `[ch]` markup.
- `db.py` stores accounts and songs in SQLite, creates the schema, scopes every
  song query to an owner, and upgrades older databases without losing rows.
- `app.py` contains the Flask routes and pages, including login, account
  administration, the manual add form, the full song editor and validation.
- `static/app.js` powers the fit-to-screen view. It measures the widest line at
  each candidate font size, chooses the largest size that fits the window, and
  packs complete sections into columns. Column breaks happen before section
  headers such as `[Verse]`, `[Chorus]`, `Verse 1:` and `C1:`; blank-line and
  balanced breaks are only fallbacks for songs without section markers. Chord
  span styling and character spacing are preserved because each column is still
  a `<pre>`.
- `templates/` and `static/` hold the UI.

## Tests

```bash
python3 -m unittest discover -s tests
```

The tests cover HTML escaping, the "no characters move" rendering guarantee,
chord auto-detection, capo transposition, the plain-text editor's
line-preserving merge, authentication and CSRF, accounts and private libraries,
roles and session invalidation, the compact song list, search and filters,
manual song entry and its validation, notes/source links/tags, the full song
editor, JSON export and import, and the in-place database upgrade. The suite
uses only the standard library, so it needs no extra test dependency.

## Good to know

- Each account has a separate library. The admin account screens manage users
  but do not expose other members' songs. Disabling an account blocks new
  logins, and a password reset signs out its existing sessions.
- The **Fit to screen** control needs JavaScript. Its choice is stored in the
  browser under `songtrove:fit`; no account or server setting is involved.
  Printing always falls back to a single-column chord sheet, even while Fit is
  active.
- **Edit song** opens the song exactly as it appears: chords stay in place and
  `[ch]`/`[tab]` markup is hidden. Change any detail or the sheet itself, then
  save everything at once. Delete whole lines to remove filler. Lines you leave
  untouched keep their chord highlighting; chord-only lines you paste or type are
  detected automatically. A line is treated as chords when every meaningful token
  is a chord name, with separators such as `|` and repeat counts such as `(x2)`
  allowed.
- Capo transposition uses the usual shapes convention: with capo 2, a written
  `G` becomes `F`. The chord with the capo then sounds as `G`, so the song stays
  in the same key while you use easier shapes. Set capo to `0` to see the
  original chords.
- You are responsible for the content you add. Chords and lyrics belong to their
  authors.
- The built-in Flask server is meant for personal/local use. For a permanent
  setup, use Gunicorn behind HTTPS as described in
  [DEPLOYMENT.md](DEPLOYMENT.md), and keep the repository private.

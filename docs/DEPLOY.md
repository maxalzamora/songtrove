# Deploying SongTrove

SongTrove runs on Django 6.1, so it needs Python 3.12 or newer. The target
below is [PythonAnywhere](https://www.pythonanywhere.com/) on the free tier,
with MySQL. It is free, needs no credit card, and keeps the database in the
same place as the code, which makes it a good fit for a personal library like
this one.

Nothing here commits secrets. The only file you create on the server is
`.env`, and it is gitignored.

Replace `<username>` with your PythonAnywhere username everywhere it appears.

---

## 1. Create the database

On the PythonAnywhere dashboard open **Databases → MySQL** and create a
database. Note the three values it shows you:

| Setting | Looks like |
| --- | --- |
| Database name | `<username>$songtrove` |
| Database host | `<username>.mysql.pythonanywhere-services.com` |
| Username | `<username>` |

The password is the one you type in that form. Keep the host exactly as
written; it must include the long domain, not `localhost`.

> Free MySQL databases are deleted unless you renew them every three months.
> Put a reminder in your calendar, or the live demo will lose its data.

## 2. Get the code onto the server

Open a **Bash console** on PythonAnywhere and clone the repository:

```bash
git clone https://github.com/maxalzamora/songtrove.git
cd songtrove
```

## 3. Create the virtualenv

```bash
python3.13 -m venv .venv          # or the newest Python available
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

On PythonAnywhere's Web tab, choose the same Python version for the web app
that you used here.

## 4. Write the environment file

```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

Edit `.env` with `nano .env` and fill in:

```dotenv
DJANGO_SECRET_KEY=<the long random string>
DJANGO_ALLOWED_HOSTS=<username>.pythonanywhere.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://<username>.pythonanywhere.com
DJANGO_TIME_ZONE=UTC

MYSQL_DATABASE=<username>$songtrove
MYSQL_USER=<username>
MYSQL_PASSWORD=<the database password>
MYSQL_HOST=<username>.mysql.pythonanywhere-services.com
MYSQL_PORT=3306
```

Quote values that contain `$` if you write them with `echo`; a text editor
needs no quoting.

## 5. Migrate, check, collect static files

```bash
export DJANGO_SETTINGS_MODULE=config.settings.prod

python manage.py check --deploy
python manage.py migrate
python manage.py collectstatic --noinput
```

`check --deploy` should report no warnings. `collectstatic` fills
`staticfiles/`, which WhiteNoise serves with hashed, compressed filenames.

## 6. Create your account and some songs

```bash
python manage.py createsuperuser
python manage.py seed_songs --user <your username>
```

The seed command adds eight public-domain songs. It is safe to run again; it
skips songs already in the account.

## 7. Point the web app at Django

On the **Web** tab:

1. **Add a new web app → Manual configuration →** the Python version from
   step 3.
2. **Source code:** `/home/<username>/songtrove`
3. **Working directory:** `/home/<username>/songtrove`
4. **Virtualenv:** `/home/<username>/songtrove/.venv`
5. Open the **WSGI configuration file** link and replace its contents with:

```python
import os
import sys

path = "/home/<username>/songtrove"
if path not in sys.path:
    sys.path.insert(0, path)

os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.prod"

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
```

6. **Reload** the app.

You do not need a static-files mapping: WhiteNoise serves `/static/` from the
Django process, so there is one place to look when something is missing.

## 8. Check it is alive

- `https://<username>.pythonanywhere.com/` shows the landing page.
- `https://<username>.pythonanywhere.com/healthz/` returns `ok`; if the
  database is down it returns `503`.
- Sign up, add a song, transpose it, and open the print view.

## 9. Updating the live site

```bash
cd ~/songtrove
git pull
source .venv/bin/activate
pip install -r requirements.txt
export DJANGO_SETTINGS_MODULE=config.settings.prod
python manage.py migrate
python manage.py collectstatic --noinput
```

Then press **Reload** on the Web tab. Static files are only re-hashed by
`collectstatic`, so a pull without it can leave the browser asking for a file
that no longer exists.

---

## When something breaks

| Symptom | Likely cause |
| --- | --- |
| 502 Bad Gateway | Wrong source path, virtualenv path, or a missing `.env` value. Check the error log on the Web tab. |
| `DisallowedHost` | `DJANGO_ALLOWED_HOSTS` does not list the domain. |
| CSRF verification failed on login | `DJANGO_CSRF_TRUSTED_ORIGINS` needs the full `https://…` origin. |
| Static files 404 | `collectstatic` was not run after the last pull. |
| `Access denied for user` | MySQL username, host, or the `<username>$songtrove` database name is wrong. |
| `Unknown database` | The database was not created, or expired; renew or recreate it. |
| Login redirect loops | Cookies are secure-only, so the site must be visited over `https`. |

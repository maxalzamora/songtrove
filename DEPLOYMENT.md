# Deployment

The app is a Flask service with password-protected accounts, private libraries,
CSRF protection, and SQLite storage. The `deploy/` files run it on a free
PythonAnywhere account or a VPS; `render.yaml` deploys it from GitHub to Render.

Do not commit `data/` or `.env`. The Songtrove database and bootstrap password
hash must stay out of the repository.

## 1. Put the project on GitHub

The project is hosted at <https://github.com/maxalzamora/songtrove>. The `main`
branch is the deployment branch. To connect a fresh clone to GitHub:

```bash
git remote add origin git@github.com:maxalzamora/songtrove.git
git push -u origin main
```

Use the HTTPS URL instead if you authenticate with a personal access token:

```bash
git remote add origin https://github.com/maxalzamora/songtrove.git
git push -u origin main
```

Check that `git status` does not list `.env`, `data/`, or `.venv/` before
committing. Run `python3 -m unittest discover -s tests` before pushing.

## 2. Set the first admin password

Passwords are stored as Werkzeug hashes, never as plain text. On a fresh
database, the first start creates an admin from `SONGTROVE_USERNAME` and
`SONGTROVE_PASSWORD_HASH`. Locally, this command writes the hash to `.env`:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python3 manage.py set-password
python3 app.py
```

Open <http://127.0.0.1:5000> and log in with the username `songtrove` and the
password you just chose. Sign in as that admin and open **Users** to add members
or additional admins.

For a hosting dashboard, print a hash and paste it into the
`SONGTROVE_PASSWORD_HASH` environment variable:

```bash
python3 manage.py hash-password
```

The `SONGTROVE_USERNAME` and `SONGTROVE_PASSWORD_HASH` values are only used when
the database has no users. After the first admin exists, change passwords from
the **Account** page or with `python3 manage.py reset-password USERNAME`. Use
`python3 manage.py list-users` to see accounts.

Never put the plain password in a repository, a build command, or a
`render.yaml` file.

## 3. Option A: PythonAnywhere (free, no card)

PythonAnywhere's free Beginner account is the simplest zero-cost option that
keeps SQLite on a persistent disk. It includes one Python web app at
`https://USERNAME.pythonanywhere.com` with free HTTPS.

Free-plan limits: no custom domain, 512 MB of file storage, one web worker, a
CPU allowance, and outbound internet access only to whitelisted hosts. The
library does not need outbound internet, so those limits are fine for a
personal collection. GitHub updates are pulled manually; there is no automatic
deploy on every push.

### Create the account and install

Create a free **Beginner** account at <https://www.pythonanywhere.com/>, then
open a **Bash console**. Check which Python version it provides:

```bash
python3 --version
```

Use that exact version when creating the web app below. Clone the repository:

```bash
cd ~
git clone https://github.com/maxalzamora/songtrove.git Songtrove
```

The repository is public, so the clone works without credentials. If you make
it private later, Git prompts for a username and password. Use your GitHub
username and a **fine-grained personal access token** with read-only access to
the repository's contents as the password. Do not put the token in the
repository or in a shell profile.

Install the dependencies and create the local environment file:

```bash
cd ~/Songtrove
python3 -m pip install --user -r requirements.txt
python3 manage.py set-password
sed -i 's/^SONGTROVE_SECURE_COOKIES=0/SONGTROVE_SECURE_COOKIES=1/' .env
```

The `set-password` command writes a hashed bootstrap password and a `SECRET_KEY`
to `.env`. The `sed` command makes the session cookie HTTPS-only. Confirm that
`.env` contains the absolute database path for this account, for example
`/home/USERNAME/Songtrove/data/songtrove.db`.

Guest access is enabled by default. On the first visit to the guest library, the
app creates a read-only member account with a few public-domain songs. It never
gets admin access and cannot modify songs. Set `SONGTROVE_GUEST=0` in `.env` to
disable and hide guest access.

### Configure the web app

In the PythonAnywhere **Web** tab:

1. Choose **Add a new web app**.
2. Choose **Manual configuration** and select the same Python version you used
   above (for example Python 3.13).
3. Set **Source code** and **Working directory** to `/home/USERNAME/Songtrove`.
4. Open the **WSGI configuration file** and replace its contents with
   `deploy/pythonanywhere_wsgi.py`. The file finds the repository at
   `~/Songtrove`.
5. Under **Static files**, add:
   - URL: `/static/`
   - Directory: `/home/USERNAME/Songtrove/static`
6. Leave **Virtualenv** blank because the packages were installed with
   `--user`.
7. Click **Reload**.

Open `https://USERNAME.pythonanywhere.com`, log in with username `songtrove`
and the password you chose above. Use **Users** to create member accounts.

### Move the existing songs

In the local app, use **Export songs** in the footer to download
`songtrove.json` for the signed-in account. On the PythonAnywhere site, log in
to that account and open **Import songs** to upload the file. The import keeps
titles, artists, tunings, capos, ratings and chord sheets.

### Update after pushing to GitHub

In the PythonAnywhere Bash console:

```bash
cd ~/Songtrove
git pull
python3 -m pip install --user -r requirements.txt
```

Then click **Reload** in the Web tab. The ignored `.env` and `data/` files are
not touched by `git pull`, so the password and songs stay in place.

## 4. Option B: Render from GitHub

The blueprint uses a paid Starter instance because Render persistent disks are
not available on the free instance. Without a disk, the SQLite database is lost
on every redeploy.

1. Push the repository to GitHub.
2. In Render, choose **New → Blueprint** and connect the repository.
3. Render reads `render.yaml` and asks for `SONGTROVE_PASSWORD_HASH`. Paste the
   hash from `python3 manage.py hash-password`. This creates the first admin on
   an empty database.
4. Apply the blueprint. Render builds the app, mounts a 1 GB disk at
   `/var/data`, and stores the database at `/var/data/songtrove.db`.
5. Open the generated `https://…onrender.com` URL, log in, and add your songs.
   Use **Users** to create accounts for other people.
6. Add a custom domain in Render if you want one. HTTPS is automatic.

Useful Render settings already in `render.yaml`:

- `gunicorn --workers 1` — one worker avoids SQLite write contention.
- `SONGTROVE_SECURE_COOKIES=1` — the session cookie is HTTPS-only.
- `/healthz` — a public health check that verifies the database connection.
- `SECRET_KEY` — generated by Render, so sessions survive restarts.

To move an existing library to Render, use **Export songs** for each account,
then log in to the deployed app and import each file into the matching account.
Keep a copy of the exports outside the host as a backup.

## 5. Option C: VPS from GitHub

These steps assume Ubuntu 24.04 or Debian 12, a domain whose DNS `A` record
points at the server, and a non-root SSH user with `sudo`.

### Install packages and create the service user

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git caddy
sudo useradd --system --create-home --home-dir /opt/songtrove --shell /bin/bash songtrove
sudo mkdir -p /var/lib/songtrove
sudo chown songtrove:songtrove /var/lib/songtrove
sudo -u songtrove git clone https://github.com/maxalzamora/songtrove.git /opt/songtrove/app
```

### Install dependencies

```bash
cd /opt/songtrove/app
sudo -u songtrove python3 -m venv .venv
sudo -u songtrove .venv/bin/pip install -r requirements.txt
```

### Create `/etc/songtrove.env`

Generate a secret and a password hash first:

```bash
python3 -c 'import secrets; print(secrets.token_hex(32))'
sudo -u songtrove /opt/songtrove/app/.venv/bin/python manage.py hash-password
```

Create the environment file with `sudoedit /etc/songtrove.env`:

```ini
SECRET_KEY=paste-the-generated-secret
SONGTROVE_USERNAME=songtrove
SONGTROVE_PASSWORD_HASH=paste-the-generated-hash
SONGTROVE_DB=/var/lib/songtrove/songtrove.db
SONGTROVE_SECURE_COOKIES=1
SONGTROVE_GUEST=1
```

Then protect it:

```bash
sudo chown root:root /etc/songtrove.env
sudo chmod 600 /etc/songtrove.env
```

### Start Gunicorn and Caddy

```bash
sudo cp deploy/songtrove.service /etc/systemd/system/songtrove.service
sudo systemctl daemon-reload
sudo systemctl enable --now songtrove
sudo systemctl status songtrove
```

Edit `deploy/Caddyfile` and replace `songtrove.example.com` with your domain,
then install it:

```bash
sudo cp deploy/Caddyfile /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

Caddy obtains and renews the HTTPS certificate automatically. Open
`https://your-domain.example` and log in.

If the server has a firewall:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### Copy the existing library database

From the computer that has the current `data/songtrove.db`:

```bash
scp data/songtrove.db your-user@your-server:/tmp/songtrove.db
```

On the server:

```bash
sudo install -o songtrove -g songtrove -m 600 /tmp/songtrove.db /var/lib/songtrove/songtrove.db
sudo rm /tmp/songtrove.db
sudo systemctl restart songtrove
```

The app migrates older schemas automatically and preserves the songs and IDs.
On the first multi-account start it creates the `users` table and assigns any
existing songs to the first admin. Add the remaining accounts from **Users**.

### Update after pushing to GitHub

```bash
sudo -u songtrove git -C /opt/songtrove/app pull --ff-only
sudo -u songtrove /opt/songtrove/app/.venv/bin/pip install -r requirements.txt
sudo systemctl restart songtrove
```

## Backups

Back up the SQLite file while the app is running only if you accept a
consistent-snapshot risk; safer options are:

- Use **Export songs** in the footer and store the JSON somewhere else. It can
  be restored with **Import songs** on any installation, but it covers only the
  signed-in account's songs.
- Stop the service, copy `/var/lib/songtrove/songtrove.db`, and start it again.
- On a VPS, run a nightly `sqlite3 /var/lib/songtrove/songtrove.db ".backup
  /var/backups/songtrove-$(date +%F).db"` job and copy those files off the
  server.

The `data/` folder is deliberately ignored by git, so a `git push` is not a
backup of the library.

## Security notes

- Use long, unique passwords and keep the repository private.
- Keep `SECRET_KEY` and `SONGTROVE_PASSWORD_HASH` in the host's secret
  environment, never in the repository. The password hash is only needed for
  the first admin; rotate passwords from the app afterward.
- The app uses one Gunicorn worker because SQLite is the database. Each account
  has a private library, and every song query is scoped to its owner. For a much
  larger deployment, move to PostgreSQL and use multiple workers.
- The login form is rate-limited only by a short failure delay. A private site
  with strong passwords is the intended use; if you need stronger protection,
  put Cloudflare Access or another identity-aware proxy in front of it.

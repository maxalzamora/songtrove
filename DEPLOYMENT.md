# Deployment

The app is a single-user Flask service with a password-protected login, CSRF
protection, and SQLite storage. The `deploy/` files run it on a free
PythonAnywhere account or a VPS; `render.yaml` deploys it from GitHub to Render.

Do not commit `data/` or `.env`. The songbook database and password hash must
stay out of the repository.

## 1. Put the project on GitHub

The project is already a Git repository with an initial commit on `main`. Create
an empty **private** repository on GitHub, then connect it and push:

```bash
cd /home/test_guitar
git remote add origin git@github.com:YOUR-NAME/songbook.git
git push -u origin main
```

Use the HTTPS URL instead if you authenticate with a personal access token:

```bash
git remote add origin https://github.com/YOUR-NAME/songbook.git
git push -u origin main
```

A private repository is recommended because chord sheets may contain
copyrighted lyrics. Check that `git status` does not list `.env`, `data/`, or
`.venv/` before committing. GitHub Actions runs the test suite on every push.

## 2. Set a password

Passwords are stored as Werkzeug hashes, never as plain text. Locally, this
command writes the hash to `.env`:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python3 manage.py set-password
python3 app.py
```

Open <http://127.0.0.1:5000> and log in with the username `songbook` and the
password you just chose.

For a hosting dashboard, print a hash and paste it into the
`SONGBOOK_PASSWORD_HASH` environment variable:

```bash
python3 manage.py hash-password
```

Never put the plain password in a repository, a build command, or a
`render.yaml` file.

## 3. Option A: PythonAnywhere (free, no card)

PythonAnywhere's free Beginner account is the simplest zero-cost option that
keeps SQLite on a persistent disk. It includes one Python web app at
`https://USERNAME.pythonanywhere.com` with free HTTPS.

Free-plan limits: no custom domain, 512 MB of file storage, one web worker, a
CPU allowance, and outbound internet access only to whitelisted hosts. The
songbook does not need outbound internet, so those limits are fine for a
personal library. GitHub updates are pulled manually; there is no automatic
deploy on every push.

### Create the account and install

Create a free **Beginner** account at <https://www.pythonanywhere.com/>, then
open a **Bash console**. Clone the repository:

```bash
cd ~
git clone https://github.com/maxalzamora/Songbook.git Songbook
```

If the repository is private, Git prompts for a username and password. Use your
GitHub username and a **fine-grained personal access token** with read-only
access to the repository's contents as the password. Do not put the token in
the repository or in a shell profile.

Install the dependencies and create the local environment file:

```bash
cd ~/Songbook
python3 -m pip install --user -r requirements.txt
python3 manage.py set-password
sed -i 's/^SONGBOOK_SECURE_COOKIES=0/SONGBOOK_SECURE_COOKIES=1/' .env
```

The `set-password` command writes a hashed password and a `SECRET_KEY` to
`.env`. The `sed` command makes the session cookie HTTPS-only. Confirm that
`.env` contains the absolute database path for this account, for example
`/home/USERNAME/Songbook/data/songbook.db`.

### Configure the web app

In the PythonAnywhere **Web** tab:

1. Choose **Add a new web app**.
2. Choose **Manual configuration** and select the same Python version you used
   above (for example Python 3.13).
3. Set **Source code** and **Working directory** to `/home/USERNAME/Songbook`.
4. Open the **WSGI configuration file** and replace its contents with
   `deploy/pythonanywhere_wsgi.py`. The file finds the repository at
   `~/Songbook`.
5. Under **Static files**, add:
   - URL: `/static/`
   - Directory: `/home/USERNAME/Songbook/static`
6. Leave **Virtualenv** blank because the packages were installed with
   `--user`.
7. Click **Reload**.

Open `https://USERNAME.pythonanywhere.com`, log in with username `songbook`
and the password you chose above.

### Move the existing songs

In the local app, use **Export songbook** in the footer to download
`songbook.json`. On the PythonAnywhere site, log in and open **Import songbook**
to upload that file. The import keeps titles, artists, tunings, capos, ratings
and chord sheets.

### Update after pushing to GitHub

In the PythonAnywhere Bash console:

```bash
cd ~/Songbook
git pull
python3 -m pip install --user -r requirements.txt
```

Then click **Reload** in the Web tab. The ignored `.env` and `data/` files are
not touched by `git pull`, so the password and songs stay in place.

## 4. Option A: Render from GitHub

The blueprint uses a paid Starter instance because Render persistent disks are
not available on the free instance. Without a disk, the SQLite database is lost
on every redeploy.

1. Push the repository to GitHub.
2. In Render, choose **New → Blueprint** and connect the repository.
3. Render reads `render.yaml` and asks for `SONGBOOK_PASSWORD_HASH`. Paste the
   hash from `python3 manage.py hash-password`.
4. Apply the blueprint. Render builds the app, mounts a 1 GB disk at
   `/var/data`, and stores the database at `/var/data/songbook.db`.
5. Open the generated `https://…onrender.com` URL, log in, and add your songs.
6. Add a custom domain in Render if you want one. HTTPS is automatic.

Useful Render settings already in `render.yaml`:

- `gunicorn --workers 1` — one worker avoids SQLite write contention.
- `SONGBOOK_SECURE_COOKIES=1` — the session cookie is HTTPS-only.
- `/healthz` — a public health check that verifies the database connection.
- `SECRET_KEY` — generated by Render, so sessions survive restarts.

To move an existing songbook to Render, use **Export songbook** in the local
app's footer, then log in to the deployed app and open **Import songbook** to
upload that JSON file. Keep a copy of the export outside the host as a backup.

## 5. Option B: VPS from GitHub

These steps assume Ubuntu 24.04 or Debian 12, a domain whose DNS `A` record
points at the server, and a non-root SSH user with `sudo`.

### Install packages and create the service user

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git caddy
sudo useradd --system --create-home --home-dir /opt/songbook --shell /bin/bash songbook
sudo mkdir -p /var/lib/songbook
sudo chown songbook:songbook /var/lib/songbook
sudo -u songbook git clone https://github.com/YOUR-NAME/songbook.git /opt/songbook/app
```

### Install dependencies

```bash
cd /opt/songbook/app
sudo -u songbook python3 -m venv .venv
sudo -u songbook .venv/bin/pip install -r requirements.txt
```

### Create `/etc/songbook.env`

Generate a secret and a password hash first:

```bash
python3 -c 'import secrets; print(secrets.token_hex(32))'
sudo -u songbook /opt/songbook/app/.venv/bin/python manage.py hash-password
```

Create the environment file with `sudoedit /etc/songbook.env`:

```ini
SECRET_KEY=paste-the-generated-secret
SONGBOOK_USERNAME=songbook
SONGBOOK_PASSWORD_HASH=paste-the-generated-hash
SONGBOOK_DB=/var/lib/songbook/songbook.db
SONGBOOK_SECURE_COOKIES=1
```

Then protect it:

```bash
sudo chown root:root /etc/songbook.env
sudo chmod 600 /etc/songbook.env
```

### Start Gunicorn and Caddy

```bash
sudo cp deploy/songbook.service /etc/systemd/system/songbook.service
sudo systemctl daemon-reload
sudo systemctl enable --now songbook
sudo systemctl status songbook
```

Edit `deploy/Caddyfile` and replace `songbook.example.com` with your domain,
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

### Copy the existing songbook database

From the computer that has the current `data/songbook.db`:

```bash
scp data/songbook.db your-user@your-server:/tmp/songbook.db
```

On the server:

```bash
sudo install -o songbook -g songbook -m 600 /tmp/songbook.db /var/lib/songbook/songbook.db
sudo rm /tmp/songbook.db
sudo systemctl restart songbook
```

The app migrates older schemas automatically and preserves the songs and IDs.

### Update after pushing to GitHub

```bash
sudo -u songbook git -C /opt/songbook/app pull --ff-only
sudo -u songbook /opt/songbook/app/.venv/bin/pip install -r requirements.txt
sudo systemctl restart songbook
```

## Backups

Back up the SQLite file while the app is running only if you accept a
consistent-snapshot risk; safer options are:

- Use **Export songbook** in the footer and store the JSON somewhere else. It
  can be restored with **Import songbook** on any installation.
- Stop the service, copy `/var/lib/songbook/songbook.db`, and start it again.
- On a VPS, run a nightly `sqlite3 /var/lib/songbook/songbook.db ".backup
  /var/backups/songbook-$(date +%F).db"` job and copy those files off the
  server.

The `data/` folder is deliberately ignored by git, so a `git push` is not a
backup of the songbook.

## Security notes

- Use a long, unique password and keep the repository private.
- Keep `SECRET_KEY` and `SONGBOOK_PASSWORD_HASH` in the host's secret
  environment, never in the repository.
- The app uses one Gunicorn worker because SQLite is the database. If the
  songbook grows into a multi-user service, move it to PostgreSQL and use
  multiple workers.
- The login form is rate-limited only by a short failure delay. A private
  single-user site with a strong password is the intended use; if you need
  stronger protection, put Cloudflare Access or another identity-aware proxy in
  front of it.

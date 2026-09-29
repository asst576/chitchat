# Setup and Development

## Requirements

- Python 3.12 or a compatible version supported by Django 5.2.
- Django 5.2 (`requirements.txt`).
- SQLite, included with Python.
- A server-side BUILD proxy key for each provider interface to enable.

The runtime uses Python's standard-library `urllib` for proxy requests. Node.js is used by the Markdown renderer safety test when available; it is not a runtime dependency. The Python suite skips that Node-based test if Node.js is unavailable.

## Local Setup

Create a virtual environment, install dependencies, and set Django environment values in the process environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export DJANGO_DEBUG=true
export DJANGO_SECRET_KEY='local-development-only-change-me'
export DJANGO_ALLOWED_HOSTS='localhost,127.0.0.1,testserver'
export DJANGO_SQLITE_PATH=''
export DJANGO_APP_BASE_PATH='/'
export DJANGO_SIGNUPS_ENABLED=false

python manage.py migrate
python manage.py createsuperuser
python manage.py provision_bootstrap_account --username BOOTSTRAP_USERNAME
python manage.py check
python manage.py test
python manage.py runserver 127.0.0.1:8000
```

Replace `BOOTSTRAP_USERNAME` with the username entered during `createsuperuser`.

`.env.example` contains placeholders but the application does not load `.env` files automatically. Configure `BUILD_OPENAI_KEY`, `BUILD_ANTHROPIC_KEY`, and/or `BUILD_GOOGLE_KEY` in a private shell or runtime secret manager. Never commit actual values. An unset key leaves that model disabled in the selector.

SQLite defaults to `<project-root>/db.sqlite3`; an empty `DJANGO_SQLITE_PATH` uses that default. Database files are ignored by Git.

For a fresh database, signup remains unavailable until a superuser and its profile/billing records exist. After the route is confirmed private, set `DJANGO_SIGNUPS_ENABLED=true` and restart the process. Signup is available only when that setting is enabled and no ownerless conversations remain.

`createsuperuser` provisions a Django authentication identity from the command line; this project does not install the Django admin site.

## Existing Database with Legacy Conversations

Do not apply the final owner constraint to an existing database until the designated bootstrap owner is created and the source database has been backed up and rehearsed. Stop any old `--noreload` worker before migration so it cannot create further ownerless conversations. Use the same SQLite path and runtime environment as the application.

1. Take an SQLite-consistent backup and rehearse restoring it. Record conversation/message counts and metadata without reading message contents.
2. Apply the nullable transition and create the operator-selected superuser:

   ```bash
   python manage.py migrate chat 0003_billingaccount_userprofile_conversation_owner_and_more --noinput
   python manage.py createsuperuser
   ```

3. Provision the selected superuser and explicitly assign the legacy rows:

   ```bash
   python manage.py provision_bootstrap_account --username BOOTSTRAP_USERNAME
   python manage.py assign_legacy_conversation_owner --username BOOTSTRAP_USERNAME
   ```

Replace `BOOTSTRAP_USERNAME` in both commands with the username created in step 2.

4. Verify all retained conversations have that owner and row counts/message ordering and metadata match the backup. The command reports counts without printing message contents.
5. Apply the final migration, which aborts if any ownerless conversations remain:

   ```bash
   python manage.py migrate --noinput
   ```

6. Only after ownership verification and the non-null migration succeed, enable signup as described above and start/restart the feature code.

Never infer an owner from the first self-registered user or delete legacy chats. The final owner migration is `0004_require_conversation_owner`.

## Runtime Settings

- `DJANGO_DEBUG`: defaults to `false`. Set `true` only for local development. If `false`, startup requires `DJANGO_SECRET_KEY`.
- `DJANGO_SECRET_KEY`: Django signing/session secret. Keep it private and out of Git.
- `DJANGO_ALLOWED_HOSTS`: comma-separated host names; configure for the actual deployment host.
- `DJANGO_CSRF_TRUSTED_ORIGINS`: comma-separated full origins when the deployment's HTTPS/reverse-proxy setup requires them.
- `DJANGO_SQLITE_PATH`: optional SQLite file path. The default is `<project-root>/db.sqlite3`.
- `DJANGO_APP_BASE_PATH`: browser-visible mount prefix; `/` locally and `/proxy/5001/` in CodeRange.
- `DJANGO_SIGNUPS_ENABLED`: allows signup only after the bootstrap superuser is provisioned and ownerless conversations are gone; defaults to `false`.
- `BUILD_OPENAI_KEY`: server-side key for the proxy's OpenAI-compatible interface.
- `BUILD_ANTHROPIC_KEY`: server-side key for the proxy's Anthropic-compatible interface.
- `BUILD_GOOGLE_KEY`: server-side key for the proxy's Gemini-compatible interface.

The proxy key names and request formats are documented at <https://proxy.litechat.ai/docs>. Do not put their values in templates, JavaScript, browser storage, source files, or logs.

## Migrations and Tests

After model changes, create/review migrations and apply them:

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py test
```

The test suite mocks the proxy boundary and makes no live or paid provider requests. It covers account setup, owner isolation, billing/profile, Markdown safety, and the legacy migration gate.

## CodeRange

The CodeRange app target is `0.0.0.0:5001`, mounted at `/proxy/5001/`. Configure a persistent `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=false`, actual `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS`, private route access, `DJANGO_APP_BASE_PATH=/proxy/5001/`, a deliberate signup setting, and writable persistent SQLite storage according to the platform. This repository does not include a CodeRange production process/static-server manifest; a `runserver --insecure` smoke process is not a production server recommendation.

The template uses `<base href="/proxy/5001/">` and relative asset references; JavaScript resolves its API root from `document.baseURI`. Django keeps `STATIC_URL = "/static/"`, so browser paths are under `/proxy/5001/static/...` and `/proxy/5001/api/...`; the reverse proxy strips the mount before forwarding to Django. Root-relative auth `Location` targets intentionally stay upstream-rooted (for example `/accounts/login/` and `/`) because CodeRange adds the mount when returning redirects to the browser. Do not prepend `DJANGO_APP_BASE_PATH` to those server redirects or the prefix will be duplicated. See [CodeRange and proxy footguns](footguns/coderange-and-proxy.md).

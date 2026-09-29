# Setup and Development

## Requirements

- Python 3.12 or a compatible Python version supported by Django 5.2.
- Django 5.2 (`requirements.txt`).
- SQLite, included with Python.
- A BUILD proxy key for each provider interface to be enabled. The proxy key values are never stored in the repository or returned to the browser.

The app uses Python's standard-library `urllib` for outbound proxy requests; it does not require a provider SDK or a separate HTTP-client dependency.

## Local Setup

Create and activate a virtual environment, install dependencies, and configure Django settings in the process environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export DJANGO_DEBUG=true
export DJANGO_SECRET_KEY='local-development-only-change-me'
export DJANGO_ALLOWED_HOSTS='localhost,127.0.0.1'
export DJANGO_SQLITE_PATH=''

python manage.py migrate
python manage.py check
python manage.py test
python manage.py runserver 127.0.0.1:8000
```

Use `BUILD_OPENAI_KEY`, `BUILD_ANTHROPIC_KEY`, and/or `BUILD_GOOGLE_KEY` as needed. Set actual values only in a private shell/runtime secret configuration. `.env.example` contains placeholders; this project does not load `.env` files automatically. An unset key leaves that model disabled in the selector.

SQLite defaults to `db.sqlite3` in the project directory. `DJANGO_SQLITE_PATH` can point to a writable persistent location; an empty value uses the default. Local database files are ignored by Git.

## Runtime Settings

- `DJANGO_DEBUG`: defaults to `false`. Set `true` only for local development. If `false`, startup requires `DJANGO_SECRET_KEY`.
- `DJANGO_SECRET_KEY`: Django signing/session secret. Keep it private and out of Git.
- `DJANGO_ALLOWED_HOSTS`: comma-separated host names; configure for the actual deployment host.
- `DJANGO_CSRF_TRUSTED_ORIGINS`: comma-separated full origins when the deployment's HTTPS/reverse-proxy setup requires them.
- `DJANGO_SQLITE_PATH`: optional SQLite file path. The default is `<project-root>/db.sqlite3`.
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

The default test suite mocks the proxy boundary and makes no live or paid provider requests.

## CodeRange

With explicit user authorization, the prior port-5001 service was stopped and LiteChat started with `runserver 0.0.0.0:5001 --noreload --insecure`, `DJANGO_DEBUG=false`, a temporary process-only signing key, and host/origin settings derived from the CodeRange proxy template. CodeRange mounts the app at `/proxy/5001/`. The template's `<base href="./">` keeps relative CSS and JavaScript URLs under that mount: `/proxy/5001/static/chat/chat.css` and `/proxy/5001/static/chat/chat.js`. JavaScript resolves its API root as `/proxy/5001/api` from `document.baseURI`. Django keeps `STATIC_URL = "/static/"` because CodeRange removes `/proxy/5001` before forwarding paths to the app. Simulated prefix-stripped requests serve both assets and the provider API with HTTP 200, and live chat create/reopen/continue flows pass through the same mapping. The user reports the workspace page loads, but this execution environment returns transport errors when fetching the external page/assets, so post-fix delivery in the user's browser remains to be confirmed. The `--insecure` option was used only to serve static assets during this smoke run and is not a production deployment recommendation. See [CodeRange and proxy footguns](footguns/coderange-and-proxy.md).

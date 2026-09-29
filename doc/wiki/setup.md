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

The current requested port for LiteChat is `5001`, but a different application already owns `127.0.0.1:5001`. A LiteChat startup attempt fails with `That port is already in use.`, and the existing listener returns 404 for LiteChat's `/healthz/` and `/api/providers/` endpoints. The incumbent service was not stopped or replaced; its owner must free/reconfigure the port or provide another CodeRange process/route allocation. Earlier local tests on `5002` do not verify the currently requested port or external CodeRange routing. CodeRange-specific host, CSRF/HTTPS, static-file, key-injection, private-access, and SQLite persistence configuration also remain to be verified. See [CodeRange and proxy footguns](footguns/coderange-and-proxy.md).

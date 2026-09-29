# CodeRange and Proxy Footguns

## CodeRange Subpath and Static Assets

ChitChat is mounted at `/proxy/5001/` and the Django worker listens on port `5001`. Set `DJANGO_APP_BASE_PATH=/proxy/5001/`. Templates use that base for browser links/forms and relative assets, while JavaScript builds its API URL from `document.baseURI`. Browser requests therefore target `/proxy/5001/static/...` and `/proxy/5001/api/...`; Django keeps `STATIC_URL = "/static/"` and receives the path after the CodeRange proxy strips the mount.

Authentication redirects use a different URL space. Django `LOGIN_URL`, `LOGIN_REDIRECT_URL`, and `LOGOUT_REDIRECT_URL` are upstream-rooted (`/accounts/login/`, `/`, and `/accounts/login/`). CodeRange adds `/proxy/5001/` to root-relative `Location` headers. Do not put the mount prefix in those settings or redirect responses will duplicate it. The login view removes an existing mount prefix from a safe `next` target before redirecting.

The app's `runserver --noreload` worker must be restarted after deploying changed templates, JavaScript, or settings; it does not load file changes automatically. Verify health, login/signup redirects, CSS/JavaScript, and API requests through the configured mount. Tests simulate `SCRIPT_NAME=/proxy/5001`; the live port-5001 worker has also served those assets and routes. External browser access, CodeRange private-access policy, TLS termination, and storage persistence remain platform-specific checks.

## Legacy Database Ownership Migration

For an existing SQLite database, take an SQLite-consistent backup and rehearse restoring/migrating a copy before touching the live schema. Record conversation/message counts and metadata without reading message contents. Stop an old `--noreload` worker before migration so it cannot create new ownerless rows.

Migration `0003` adds a nullable owner. Create the operator-selected superuser with `createsuperuser`, replacing `BOOTSTRAP_USERNAME` below with that account's username. Run `provision_bootstrap_account --username BOOTSTRAP_USERNAME`, then `assign_legacy_conversation_owner --username BOOTSTRAP_USERNAME`. Verify every retained conversation is owned by that account and the original message count/order is preserved. Only then apply the remaining migration; `0004_require_conversation_owner` aborts if any ownerless rows remain. Signup remains disabled until the backfill and non-null migration succeed. Never guess an owner, assign chats to the first self-registered user, or delete legacy rows.

## Server-Side Proxy Keys

The proxy docs name `BUILD_OPENAI_KEY`, `BUILD_ANTHROPIC_KEY`, and `BUILD_GOOGLE_KEY`. The app checks the relevant variable and sends it only from Django to the fixed proxy host. `.env.example` values are placeholders, not working keys. Verify key injection into the running worker without printing or sharing values.

Never paste actual key values into Git-tracked files, issue descriptions, logs, frontend configuration, or browser storage. Configure them with the platform's secret/environment mechanism. The app does not load `.env` automatically.

## Provider Labels Are Proxy Interfaces

The public proxy docs state that the OpenAI-, Anthropic-, and Gemini-compatible interfaces all use DeepSeek Flash and do not reproduce the named providers' model behavior. The UI discloses this. Do not describe the choices as distinct upstream OpenAI, Anthropic, and Google models.

No model-list endpoint is documented. Only the three exact model IDs listed in the proxy docs are currently allowlisted. Do not add model names by guessing.

## Signup and Account Provisioning

Signup defaults to disabled. Enabling `DJANGO_SIGNUPS_ENABLED` alone is insufficient: signup also requires a provisioned superuser with profile/billing records and zero ownerless conversations. Keep the CodeRange route private even when signup is enabled; app-level authentication does not replace platform access control. There is no password-reset or email-recovery flow.

## Django Deployment Settings

`DJANGO_DEBUG` defaults to false, and production mode refuses to start without `DJANGO_SECRET_KEY`. Configure `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS` for the actual CodeRange hostname. Forwarded HTTPS headers, secure cookies, static serving, and persistent SQLite storage must be matched to the platform's real setup rather than guessed. A local `runserver` check alone does not validate these settings.

## Non-Streaming and Context Limits

The proxy documents streaming variants, but the MVP intentionally uses whole-response requests. It has no cancellation support. Long histories are sent in full; automatic truncation or summarization is not implemented. If the proxy rejects an oversized context, shorten the conversation rather than silently dropping turns.

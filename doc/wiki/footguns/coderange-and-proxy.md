# CodeRange and Proxy Footguns

## Port 5001 Is Already In Use

During implementation, `127.0.0.1:5001` responded with a different Django application (including unrelated admin, accounts, campaigns, and feed routes). The user explicitly requested that this existing service remain running. LiteChat did not stop or replace it, and LiteChat has not been verified as reachable on port `5001`.

The user selected port `5002` for LiteChat. A local Django smoke test on `127.0.0.1:5002` passed. Do not stop or replace the existing `5001` process. No CodeRange route mapping for `5002` is available in this workspace, so it is not yet possible to determine whether the platform exposes that port externally. Obtain/verify its route mapping before claiming the app is reachable. Local Django test-client or loopback success does not verify CodeRange routing.

## Server-Side Proxy Keys

The proxy docs name `BUILD_OPENAI_KEY`, `BUILD_ANTHROPIC_KEY`, and `BUILD_GOOGLE_KEY`. The app checks the relevant variable and sends it only from Django to the fixed proxy host. `.env.example` values are placeholders, not working keys. Although the user reports that these variables are configured in CodeRange, they were absent from this execution process, so live provider requests were skipped. Verify injection into the app worker without printing or sharing values.

Never paste actual key values into Git-tracked files, issue descriptions, logs, frontend configuration, or browser storage. Configure them with the platform's secret/environment mechanism. The app does not load `.env` automatically.

## Provider Labels Are Proxy Interfaces

The public proxy docs state that the OpenAI-, Anthropic-, and Gemini-compatible interfaces all use DeepSeek Flash and do not reproduce the named providers' model behavior. The UI discloses this. Do not describe the choices as distinct upstream OpenAI, Anthropic, and Google models.

No model-list endpoint is documented. Only the three exact model IDs listed in the proxy docs are currently allowlisted. Do not add model names by guessing.

## Private Single-User Deployment

The application has no built-in authentication or per-user conversation isolation. The user selected private single-user use. Keep the CodeRange route private; do not expose it on a public/shared host without adding authentication and ownership checks.

## Django Deployment Settings

`DJANGO_DEBUG` defaults to false, and production mode refuses to start without `DJANGO_SECRET_KEY`. Configure `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS` for the actual CodeRange hostname. Forwarded HTTPS headers, secure cookies, static serving, and persistent SQLite storage must be matched to the platform's real setup rather than guessed. A local `runserver` check alone does not validate these settings.

## Non-Streaming and Context Limits

The proxy documents streaming variants, but the MVP intentionally uses whole-response requests. It has no cancellation support. Long histories are sent in full; automatic truncation or summarization is not implemented. If the proxy rejects an oversized context, shorten the conversation rather than silently dropping turns.

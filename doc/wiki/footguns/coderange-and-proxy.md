# CodeRange and Proxy Footguns

## LiteChat Cannot Bind Port 5001 Yet

The current requested LiteChat port is `5001`, but `127.0.0.1:5001` is occupied by a different application. A startup attempt for LiteChat fails with `That port is already in use.`; the listener returns HTTP 404 for LiteChat's `/healthz/` and `/api/providers/` endpoints. TCP reachability therefore does not mean LiteChat is serving there.

Earlier, port `5002` was selected to preserve the incumbent service, and a local Django smoke test there passed. The latest request changes the target back to `5001`; the existing process was not stopped or replaced. Its owner must authorize freeing/reconfiguring `5001`, or the platform must provide a different process/route allocation. No external CodeRange route mapping is available in this workspace. Local Django test-client or loopback success does not verify CodeRange routing.

## Server-Side Proxy Keys

The proxy docs name `BUILD_OPENAI_KEY`, `BUILD_ANTHROPIC_KEY`, and `BUILD_GOOGLE_KEY`. The app checks the relevant variable and sends it only from Django to the fixed proxy host. `.env.example` values are placeholders, not working keys. All three variables were present in the current execution environment, and live OpenAI-, Anthropic-, and Google-compatible proxy requests each returned HTTP 200 with a complete parsed response. This does not independently verify injection into a separately managed CodeRange worker. Verify worker configuration without printing or sharing values.

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

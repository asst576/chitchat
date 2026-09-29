# CodeRange and Proxy Footguns

## Distinguish Local Port 5001 From CodeRange Reachability

The prior port-5001 service was stopped only after explicit user authorization. LiteChat now binds `0.0.0.0:5001`. Its health, workspace, CSS/JavaScript, provider catalog, live create/reopen/continue chat flow, and safe invalid-model response pass through the local container interface.

The environment's `VSCODE_PROXY_URI` uses the route pattern `/proxy/{{port}}/`; for port 5001, the browser URL is `https://<workspace-host>.coderange.net/proxy/5001/`. The route hostname resolves, but requesting its `/healthz/` endpoint from this execution environment fails with connection refused (errno 111). Local loopback/container-interface success does not establish external CodeRange reachability or static serving. The CodeRange platform owner must verify/enable the private port-5001 forwarding rule and HTTPS ingress. This execution environment cannot distinguish a platform ingress issue from an egress restriction. Private-access policy and SQLite persistence across restarts also remain unverified.

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

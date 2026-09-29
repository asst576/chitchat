# LiteChat MVP Implementation Plan

- Plan timestamp: `1790658908`
- Plan date: 2026-09-29
- Primary basis: `doc/study/1790658228_litechat_core_functionality_feasibility.md`
- Current repository state at planning: clean `main`; repository contains `AGENTS.md` and the completed study only; no Django application, tests, dependency manifest, canonical docs, or CodeRange config exists.

## Execution Status

**Partially executed, blocked on external CodeRange route verification and deployment configuration.** Django/SQLite chat behavior, the documented non-streaming proxy integrations, tests, living documentation, and live calls through all three proxy interfaces are verified on `feature/litechat-mvp`. Do not merge yet. With explicit user authorization, the prior port-5001 service was stopped and LiteChat now starts on `0.0.0.0:5001`. The workspace/container interface serves the UI, static assets, API, and chat flows, but requests through the discovered external CodeRange port-proxy URL fail with connection refused (errno 111). CodeRange external routing, private access enforcement, and SQLite persistence across restarts remain unverified.

## Execution Notes

- Execution branch: `feature/litechat-mvp`.
- The user supplied `https://proxy.litechat.ai` and clarified that one proxy-compatible key is intended per provider. Public authoritative docs were located at `https://proxy.litechat.ai/docs` (revision 2026-09-19), including provider-specific endpoint contracts. The unrelated `/home/coder` application's generic `LLM_API_URL` remains unused.
- Verified contracts: OpenAI `POST /openai/v1/chat/completions`, `Authorization: Bearer ...`, model `gpt-5.6-luna`; Anthropic `POST /anthropic/v1/messages`, `x-api-key` plus `anthropic-version: 2023-06-01`, model `claude-haiku-4-5-20251001`; Google `POST /google/v1beta/models/gemini-3.8-flash:generateContent`, `x-goog-api-key`, model `gemini-3.8-flash`. The docs name server environment variables `BUILD_OPENAI_KEY`, `BUILD_ANTHROPIC_KEY`, and `BUILD_GOOGLE_KEY`. No model catalog endpoint or request timeout/cancellation contract is documented; the app uses a fixed allowlist and its own bounded 90-second non-streaming timeout.
- The proxy docs state all three provider interfaces are backed by DeepSeek Flash and do not reproduce the named providers' model behavior. The UI and living docs must make that limitation clear; provider names identify compatible API interfaces, not distinct upstream model behavior.
- The user reports `BUILD_OPENAI_KEY`, `BUILD_ANTHROPIC_KEY`, and `BUILD_GOOGLE_KEY` are configured. All three were present in this execution environment, and live requests through the application adapters each returned HTTP 200 with a complete parsed response. Only provider, outcome, and status were recorded; no key values or response text were printed or written.
- The user resolved the app audience as private single-user, initially asked to preserve the existing service on port `5001` by using `5002`, and later explicitly authorized stopping the incumbent and switching LiteChat to `5001`. The previous listener was stopped; LiteChat now owns `0.0.0.0:5001`. The app will not add user registration; deployment must remain private.
- Runtime key visibility is verified for this execution process by successful live calls; injection into a separately managed, persistent CodeRange worker is not independently verified. Do not request or print key values.
- Runtime inspection found Python 3.12.3 and Django 5.2.17 in `/home/coder/.venv`; system `python3` has no Django installed. No `requests` package is installed in that virtualenv. The target repository itself had no code/config before execution.
- B3 is partially complete: environment-driven Django settings, SQLite path, host/origin configuration, and static settings exist; CodeRange-specific host/CSRF/HTTPS/static-serving values remain unverified.
- With explicit user authorization, the prior port-5001 process (PID 283318) received `SIGTERM`, and the port became free. LiteChat was started with `runserver 0.0.0.0:5001 --noreload --insecure`, `DJANGO_DEBUG=false`, a generated process-only signing key, and the discovered CodeRange route host/origin allowlisted. The key value was not printed or persisted.
- LiteChat health returned HTTP 200 on the container interface; the workspace, CSS, JavaScript, and provider catalog also returned HTTP 200 locally. A live OpenAI chat was created, reopened from history, and continued with Google; all responses completed and the four-message smoke conversation was removed afterward. An invalid model safely returned HTTP 400 with `unsupported_model`.
- `VSCODE_PROXY_URI` supplied the CodeRange port-proxy template. Requests to its port-5001 `/healthz/` route failed with `ConnectionRefusedError` (errno 111), and external static/API/chat flows therefore remain unverified. This environment also lacks evidence for CodeRange private-access policy and SQLite persistence across restarts.

## OPEN QUESTIONS

The proxy contract, initial provider/model identifiers, key variable names, live proxy connectivity in this execution environment, private single-user audience, and local port-5001 ownership have been resolved. Remaining external inputs are:

1. **External CodeRange route:** The port-proxy template is available, but requests to the port-5001 health route return a connection-refused transport error from this execution environment. The platform route owner must restore/enable forwarding or provide a reachable CodeRange URL so external UI, static, and chat flows can be verified.
2. **CodeRange runtime configuration:** Confirm the deployed app worker receives its secrets, uses the correct host/CSRF/HTTPS settings, enforces private access, and stores SQLite data persistently. Live calls and local HTTP flows only prove the current execution process can reach the proxy and the local server.

Streaming is documented by the proxy but is deferred for this MVP because it is not mandatory and the external CodeRange serving path cannot currently be verified.

## Goal

Build a small, secure LiteChat-style application using Django, Python, Django templates, HTML, CSS, JavaScript, and SQLite. Users can start chats, choose an actually available provider/model, send prompts through a verified server-side proxy, receive responses, preserve multi-turn context from stored messages, and reopen saved chat history. The app must be tested through a mocked proxy boundary and verified on the currently requested CodeRange port `5001`, subject to resolving the unrelated listener conflict.

## Scope

- Establish a runnable Django project and chat app in the currently empty application workspace.
- Configure SQLite, Django static/template handling, and migrations.
- Implement `Conversation` and `Message` persistence with deterministic message ordering and provider/model attribution.
- Build a basic responsive chat workspace with history, new-chat behavior, provider/model selection, transcript, composer, loading/empty/error states, and vanilla JavaScript interactions.
- Persist messages and reconstruct provider-neutral multi-turn context from stored, successful messages.
- Make server-side requests only to the LiteChat proxy after its real contract has been verified.
- Support OpenAI, Anthropic, and Google only to the extent the verified proxy explicitly supports them; expose only configured, enabled models.
- Read proxy/provider credentials from confirmed environment variables; never expose or commit secrets.
- Handle provider/proxy failures safely and test with a mocked proxy.
- Validate startup/reachability and expected configuration on the currently requested CodeRange port `5001`.
- Add/update living setup, architecture, feature, testing, environment-variable, CodeRange, and proxy limitation documentation after behavior exists.

## Out of Scope

- File uploads, attachments, image input, and other multimodal input.
- Web search, browsing, citations, or external retrieval.
- Agents, tools, MCP, workflows, prompt libraries, rules, tags, and plugins/mods.
- Billing dashboards, user quotas, usage analytics, or provider spend management UI.
- Model racing, parallel comparison, or regenerate-with-another-model.
- Projects, nested workspaces, Git sync, virtual filesystems, conversation import/export, custom themes, or multi-database support.
- Account registration/password reset unless the audience decision requires authenticated multi-user access; if it does, authentication and ownership are in scope as a prerequisite, not an optional enhancement.
- Mandatory streaming. Do not implement provider wire behavior based on assumptions.
- Automatic AI-generated conversation titles; use a bounded title derived from the first prompt or a neutral default.

## Assumptions

- The study is the primary product/architecture reference. The public LiteChat application is not an implementation template; its browser-only React/IndexedDB architecture is not carried over.
- Django is the sole application backend and calls the proxy from the server. The browser never calls an LLM provider or proxy directly.
- Use a provider-neutral internal message format and adapt it only to the verified proxy schema. The proxy may normalize provider differences, but this must be proven by its documentation/tests.
- Use the exact supported provider/model identifiers from proxy documentation/catalog or an explicit server-side allowlist. Do not hardcode speculative model names.
- The MVP stores text messages only and reconstructs conversation context on every turn from SQLite.
- SQLite is acceptable for a low/modest-traffic, single-instance MVP. Verify the database path is writable and persistent enough for CodeRange's runtime.
- User prompts and assistant output are untrusted text. Preserve Django autoescaping; rich Markdown rendering is not needed for the initial version.
- The final supported Django/Python versions and outbound HTTP dependency will be selected based on the installed CodeRange runtime and verified proxy/stream contract; add only required dependencies.
- The plan document is not approval to begin implementation. A later explicit `execute plan` instruction is required.

## Architecture

Use a small Django MVT application with same-origin browser requests:

`Django templates + CSS/JavaScript -> Django views/URLs -> conversation service -> proxy client -> verified LiteChat proxy -> enabled upstream provider/model`

- **Templates and static assets:** render the chat workspace and history shell; JavaScript submits same-origin requests, updates history/transcript and pending/error UI, and handles SSE only if the conditional streaming task is approved by evidence.
- **Views and URLs:** render the page and expose narrow endpoints for provider choices, conversation history, conversation retrieval/creation, and message submission. Enforce HTTP method, CSRF, input validation, and ownership rules at the server boundary.
- **Conversation service:** create/update records, build ordered context, persist user prompts and assistant response state, set titles/timestamps, and prevent incomplete/failed responses from becoming context by default.
- **Provider catalog:** return only providers/models verified as supported and enabled. Use a proxy catalog if one is documented and practical; otherwise use a small server-side allowlist backed by confirmed configuration.
- **Proxy client:** own all outbound HTTP details, confirmed authentication, timeouts, provider/model identifiers, request/response mapping, safe error translation, and optional stream decoding. Never accept a proxy URL from the browser.
- **Persistence:** SQLite via Django ORM. Conversation and message relationships are migrated and tested before the UI depends on them.
- **Configuration/security:** keep `SECRET_KEY`, proxy/provider credentials, and any proxy base URL in runtime environment/secret configuration. Commit placeholder examples only after exact variable names are confirmed. Keep `.env`, SQLite database files, and secrets out of Git.

Candidate endpoint surface (adjust only if the implementation reveals a concrete need):

- `GET /` renders the workspace.
- `GET /api/providers/` returns enabled providers and model identifiers/labels.
- `GET /api/conversations/` returns recent conversation summaries.
- `POST /api/conversations/` creates an empty conversation if explicit creation is selected; alternatively, create lazily on the first prompt to avoid empty records.
- `GET /api/conversations/<id>/` returns one conversation and its ordered messages.
- `POST /api/conversations/<id>/messages/` persists/submits a user prompt and returns a completed response or, conditionally, an SSE stream.

Keep rename/delete out of the initial endpoint set unless the history UI demonstrates a concrete MVP need. Any conversation lookup must apply the chosen single-user/multi-user access boundary.

## Likely Files / Areas to Change

The exact project package name can be chosen during execution; these are likely areas, not existing files:

- `requirements.txt` (or the repository's chosen minimal Python dependency manifest), `.gitignore`, and placeholder-only environment example if needed.
- `manage.py` and a Django project package such as `config/` containing `settings.py`, root `urls.py`, and ASGI/WSGI entry points.
- `chat/` app: `apps.py`, `models.py`, `admin.py` only if useful for local inspection, `urls.py`, `views.py`, request validation/forms, service modules, migrations, and tests.
- `chat/services/conversations.py` for message/context/persistence orchestration.
- `chat/services/proxy_client.py` and possibly `chat/services/providers.py` for verified proxy and catalog mapping.
- `templates/chat/index.html` plus small reusable template partials as useful.
- `static/chat/chat.css` and `static/chat/chat.js`.
- `doc/wiki/` living documentation and `doc/wiki/footguns/` setup warnings.
- SQLite database file is runtime-generated and must be ignored, not committed.

## Implementation Task Board

### A. Preflight and Contract Gate

- [x] **A1. Verify the LiteChat proxy before writing proxy integration code.** Authoritative docs at `https://proxy.litechat.ai/docs` and provider pages specify the base URL, provider-specific endpoints/authentication/request/response formats, documented model IDs, and error statuses. No model-catalog endpoint, timeout, or cancellation contract is documented. No live request was made during initial contract discovery; subsequent live verification is recorded in D6 and H4.
- [x] **A2. Resolve the OPEN QUESTIONS.** The user confirmed private single-user use and one key per provider. The user later authorized stopping the incumbent port-5001 service; it was stopped and LiteChat now binds that port. Proxy docs confirmed the three interfaces, model IDs, and `BUILD_*_KEY` names; the current execution environment has all three keys. External CodeRange forwarding remains blocked.
- [x] **A3. Record the verified integration decision.** The non-secret proxy/provider/model/auth contract and its DeepSeek Flash behavior are recorded in Execution Notes. Secrets are not recorded.
- [x] **A4. Decide streaming conditionally.** Proxy SSE variants are documented, but the external CodeRange serving path cannot be tested while port forwarding is refusing connections. The MVP uses non-streaming requests; streaming is not a release blocker.

### B. Django and SQLite Foundation

- [x] **B1. Inspect available Python/CodeRange runtime constraints** and select a compatible, minimal Django version and outbound HTTP dependency only after checking whether the standard library or an existing dependency is adequate. Python 3.12.3 and Django 5.2.17 are available in `/home/coder/.venv`; use the Django 5.2 series. No outbound HTTP dependency was added; standard-library `urllib` implements the verified non-streaming contract.
- [x] **B2. Create the Django project and `chat` app** with `manage.py`, settings, root URL configuration, ASGI/WSGI entry points, template/static configuration, and a minimal page route. Added `config/`, `chat/`, and a neutral template/health endpoint.
- [ ] **B3. Configure runtime settings safely:** SQLite path/default, `DEBUG`, environment-derived `SECRET_KEY`, `ALLOWED_HOSTS`, static settings, and deployment-specific CSRF/HTTPS proxy settings based on verified platform behavior. Do not hardcode production secrets or trust proxy headers without confirmation. **Partial:** base settings are environment-driven, `DEBUG` defaults off, and production startup requires `DJANGO_SECRET_KEY`; CodeRange-specific values remain pending platform information.
- [x] **B4. Add dependency and ignore configuration.** Pin or constrain only required runtime dependencies; ignore `.env`, local database files, caches, and generated artifacts. Add an environment example with placeholder values only and confirmed variable names only. Added Django 5.2 constraints, `.gitignore`, and `.env.example` with Django settings and confirmed `BUILD_*_KEY` names using placeholders only.
- [x] **B5. Run baseline Django checks** and confirm a fresh local SQLite database can be created. Record exact commands/results in the execution notes. `manage.py check` passed; built-in migrations applied to SQLite; two foundation tests passed; `makemigrations --check --dry-run` reported no changes; development client returned HTTP 200 for `/` and `/healthz/`; production settings correctly rejected a missing `DJANGO_SECRET_KEY`.

### C. Models and Migrations

- [x] **C1. Implement `Conversation`** with identifier, bounded title, selected provider/model IDs, timestamps, and an owner relation if required by the resolved audience decision. The selected private single-user scope has no user relation; deployment must remain private.
- [x] **C2. Implement `Message`** with conversation foreign key/cascade behavior, constrained role, text content, timestamp, deterministic ordering, assistant completion/failure status as required by the chosen send/stream lifecycle, and provider/model attribution for assistant responses.
- [x] **C3. Add useful indexes and database constraints** for conversation history ordering, message ordering, valid statuses/roles, and per-user filtering if applicable. Keep the schema minimal; do not add a project/interaction abstraction without a demonstrated need. Added recent-conversation/message-order indexes and database check constraints for provider, role, and status values.
- [x] **C4. Generate and review migrations**, then verify a fresh database migrates and tests cover cascade deletion, ordering, timestamps, and model constraints. Added `0001_initial.py` and a follow-up constraint migration; SQLite migrations and test-database creation pass.

### D. Provider Catalog and Secure Proxy Boundary

- [x] **D1. Implement a server-side provider/model catalog** backed by the verified proxy catalog endpoint or confirmed server-side allowlist. Expose only enabled IDs and safe display labels; never return credentials or arbitrary upstream endpoints. Implemented a fixed three-model allowlist from proxy docs; no model-list endpoint is documented.
- [x] **D2. Add provider/model validation** so all user-submitted selections are checked against currently enabled choices before persistence or proxy calls. Support OpenAI, Anthropic, and Google only where A1/A2 verified availability. Unknown IDs are rejected before database creation or network requests.
- [x] **D3. Implement the proxy client against the confirmed contract only.** Load URL/auth from server environment, validate response shape, apply bounded connection/read timeouts and request limits, and map the provider-neutral prompt/context to the exact documented request. Keep provider-specific protocol conversion in this boundary if the proxy does not normalize it. Implemented the three documented non-streaming formats with fixed host, provider-specific auth/header/body mapping, safe response parsing, a 90-second timeout, and a 2,000,000-byte response cap.
- [x] **D4. Keep secrets server-only.** Verify proxy/provider keys are absent from templates, rendered HTML, JavaScript, JSON responses, logs, errors, Git-tracked configuration, and browser storage. Add a safe missing-configuration response. Only environment-variable names/placeholders are tracked; catalog responses expose configured booleans, never key values. Tests assert key values do not appear in returned content.
- [x] **D5. Add proxy-client tests with mocked HTTP** for successful response, auth/config failure, unsupported model, rate limit, upstream 5xx, malformed body, timeout, and network failure. If streaming is selected, also test framing, end-of-stream, disconnect, and cancellation behavior. Covered provider successes, auth/gateway/rate failures, malformed/incomplete responses, missing keys, invalid models, timeouts, and network errors; streaming tests do not apply.
- [x] **D6. Run live smoke requests through the verified proxy for each configured provider** after the server process can see the documented keys. Used the short prompt `Reply with exactly OK.` OpenAI: success/complete, HTTP 200; Anthropic: success/complete, HTTP 200; Google: success/complete, HTTP 200. Response text and key values were not printed or written.

### E. Conversation and Message Flows

- [x] **E1. Implement recent conversation listing and conversation detail loading** with newest-activity ordering, deterministic message ordering, and ownership filtering where applicable. Implemented newest-first history and created-time/ID message ordering; private single-user deployment has no owner field.
- [x] **E2. Implement new-chat behavior** in a way that does not leave abandoned empty database rows (prefer creating the conversation on first submitted prompt unless the UI requires explicit creation). Initialize it with the selected provider/model. The new-chat action resets client state; persistence is lazy on first prompt.
- [x] **E3. Implement message submission orchestration.** Validate prompt/provider/model and conversation access; persist the user message before outbound proxy work; build context from ordered successful stored turns plus the new prompt; call the proxy; persist assistant content/status/model attribution on success; update title from a bounded first prompt and conversation activity timestamp.
- [x] **E4. Handle unsuccessful and incomplete turns.** Preserve the user prompt, mark or report assistant failure safely, exclude failed/partial assistant output from later context by default, and make retry behavior avoid duplicating the user message. Prevent duplicate/in-flight sends as practical for a single-instance SQLite MVP. A regression test caught and fixed inclusion of a prior failed user turn in later context; explicit retry reuses rather than duplicates its prompt.
- [x] **E5. Keep multi-turn context stateless at the provider boundary.** Tests must prove prior user/assistant messages are reconstructed from SQLite in the correct order and that historical provider/model attribution remains unchanged if a later turn selects a different supported model. Covered by service and endpoint tests.
- [x] **E6. Add same-origin CSRF-protected views/URLs** for provider choices, history, loading a chat, creating a conversation if needed, and submitting a message. Return stable application-level error categories and appropriate status codes, not raw proxy errors or tracebacks. Added provider/history/detail/new-message/conversation-message/retry endpoints under Django CSRF middleware.

### F. Chat Workspace UI

- [x] **F1. Build the Django-template chat shell** with history navigation, new-chat action, current provider/model controls, message transcript, composer, and clear empty state.
- [x] **F2. Add responsive CSS** for desktop and mobile, readable user/assistant distinction, long-message wrapping, keyboard focus, and accessible labels/status announcements. Mobile history is horizontally browsable rather than hidden.
- [x] **F3. Add JavaScript for new chat, provider/model selection, opening history, prompt submission, and transcript/history refresh** using same-origin endpoints and CSRF tokens. Do not put provider keys or proxy authentication in JavaScript.
- [x] **F4. Implement loading and failure states:** disable or guard duplicate submit while pending, preserve the prompt on request failure, show a safe retry/actionable message, and distinguish empty history from loading and error states.
- [x] **F5. Render message content safely.** Use escaped plain text initially. Do not mark model output safe or add unsanitized Markdown/HTML. DOM content uses `textContent`; no `innerHTML` or browser storage is used.
- [x] **F6. If and only if A4 approved streaming, implement browser SSE consumption and incremental UI updates** with complete/failed/cancelled states. Otherwise verify normal response UX and document that responses are non-streaming. Non-streaming is selected for this MVP; no SSE code was added.

### G. Application Tests and End-to-End Verification

- [x] **G1. Add model tests** for persistence, stable ordering, cascade deletion, titles/timestamps, roles/statuses, and ownership boundaries if applicable.
- [x] **G2. Add conversation-service tests** for new chats, prompt persistence, context reconstruction, provider/model validation, failed response exclusion, retry without duplicate prompt, and conversation history updates.
- [x] **G3. Add Django view tests** for page rendering, new chat/history/reopen flows, message submission, CSRF, invalid input, missing proxy configuration, not-found/unauthorized conversations, and sanitized failures.
- [x] **G4. Add security regression tests** ensuring secret values never appear in HTML/JSON/errors/log-capture, model output is escaped, arbitrary provider/model/endpoint values are rejected, and cross-user access is denied if accounts are required. Provider responses do not include key values; browser rendering uses text nodes only; CSRF and arbitrary-model rejection are tested. Cross-user isolation is not applicable to the selected private single-user design and depends on private deployment access control.
- [x] **G5. Add mocked-proxy integration tests** that run the Django-to-service-to-SQLite path without live provider credentials, paid requests, or network access.
- [x] **G6. Run the full test suite, `python manage.py check`, and fresh-database migrations.** Fix implementation-caused issues and record commands/results. Live provider calls must remain optional and explicitly configured. Final isolated checks used `DJANGO_DEBUG=true` and `DJANGO_SQLITE_PATH=:memory:`: `manage.py test` passed all 24 tests; `manage.py check` reported no issues; `makemigrations --check --dry-run` reported no changes; `manage.py migrate --noinput` applied all migrations to a fresh in-memory database.

### H. CodeRange Startup and Validation

- [ ] **H1. Verify CodeRange runtime instructions and configuration** including process command, exposed host/interface, required host/CSRF settings, injected environment-variable names, outbound proxy access, and persistent writable SQLite location. Do not record actual secret values. **Partial:** all three keys and outbound proxy access were verified in this execution environment; CodeRange worker configuration, external route mapping, private access, and persistent-volume/runtime configuration remain unavailable here.
- [x] **H2. Start the application on the currently requested port `5001`** using the required CodeRange-compatible command and bind address. Identify port conflicts rather than silently changing ports. Started `runserver 0.0.0.0:5001 --noreload --insecure` with `DJANGO_DEBUG=false`; the server is listening on all interfaces and the health endpoint returns HTTP 200 through the container interface. The separate external CodeRange route is tracked under H3.
- [ ] **H3. Verify reachability and static assets** through the CodeRange endpoint, not only local Django `runserver`. **Blocked:** the discovered `VSCODE_PROXY_URI` port-5001 route fails with connection refused (errno 111). Local UI, CSS, JavaScript, provider API, and health checks pass, but external CodeRange route/static serving is not verified.
- [ ] **H4. Exercise key flows on CodeRange:** create a new chat, select an enabled provider/model, submit and receive a response using a mock/stub or explicitly approved configured proxy, reload and reopen history, continue with prior context, and safely display a proxy failure. Locally through the server HTTP interface, a live OpenAI chat was created, reopened, and continued with Google; responses completed, and invalid-model handling returned a safe 400. The external CodeRange route failure prevents marking the CodeRange flows complete.
- [x] **H5. If streaming was selected, verify the real CodeRange serving/reverse-proxy path** does not buffer or prematurely terminate SSE and that disconnects close upstream work when supported. Not applicable: the MVP uses non-streaming requests.
- [ ] **H6. Verify SQLite persistence across the expected restart lifecycle** or document if CodeRange storage is ephemeral and requires a persistent volume/configuration change. Local SQLite migrations and file-backed settings work; CodeRange storage persistence is unverified.

### I. Documentation

- [x] **I1. Add living setup/overview documentation under `doc/wiki/`** covering only implemented features, supported provider/model discovery, Python dependency installation, migrations, startup, and tests. Added `overview.md` and `setup.md`.
- [x] **I2. Document the actual proxy integration contract at a safe level** including endpoint semantics, confirmed environment-variable names, request flow, supported provider/model subset, streaming behavior, and safe placeholder values. Never include real credentials or undocumented guesses. Added provider-specific contract and DeepSeek Flash caveat in `architecture.md`.
- [x] **I3. Add a CodeRange/setup footgun document under `doc/wiki/footguns/`** for port `5001`, required injected configuration, SQLite persistence, host/CSRF/reverse-proxy settings, and common startup/proxy failures actually encountered. Added `coderange-and-proxy.md` and recorded unresolved platform-specific values without inventing them.
- [x] **I4. Document known limitations** such as non-streaming behavior when selected, text-only messages, no user accounts if approved private single-user use, no automatic context compaction, and unsupported providers/models. Do not describe out-of-scope features as implemented.
- [x] **I5. Review all docs against the actual code after implementation** and commit docs with the implementation work as focused changes; do not rewrite the historical study. Reviewed docs against the current code and left the study unchanged.

## Testing

The default test suite is offline and mocks the proxy boundary. It covers provider adapters, models/migrations, context order, provider catalog/validation, message outcomes/retries, CSRF, safe errors, and key non-disclosure. No real provider credentials or paid API calls are required. Streaming is not implemented.

## Validation

- `python manage.py check` passes with the documented test/development environment.
- Fresh SQLite database migrations apply successfully; tests pass against an isolated test database.
- Provider/model choices match only the verified proxy catalog/allowlist and all outbound calls use the server-side proxy client.
- New chat, prompt/response, saved history, reopen, and context continuation work with a mocked proxy; unsupported selection and upstream failure paths are safe.
- Credentials do not appear in browser output or tracked files.
- Live proxy smoke requests through the application adapter succeeded for OpenAI, Anthropic, and Google with HTTP 200 and complete parsed responses; only provider, outcome, and status were recorded. LiteChat now binds `0.0.0.0:5001`; its local health, workspace, CSS, JavaScript, provider catalog, live create/reopen/continue flow, and invalid-model response all passed. The external CodeRange port-proxy route returns connection refused (errno 111), so external reachability/static/chat flows, private access, and database persistence remain unverified.
- If streaming is absent or impractical, the UI uses non-streaming requests and documentation explicitly records the limitation.

## Documentation Updates

Update only living documentation under `doc/wiki/` and `doc/wiki/footguns/` as part of execution. Suggested files are `doc/wiki/overview.md`, `doc/wiki/setup.md`, `doc/wiki/architecture.md`, and `doc/wiki/footguns/coderange-and-proxy.md`. Exact filenames may be consolidated if that keeps the documentation concise. Include actual environment-variable names with placeholders, provider/model availability, database/migration setup, tests, CodeRange startup/reachability, and known limitations. Leave the study as a historical artifact.

## Completion Criteria

- All applicable implementation and documentation checklist items are completed, with conditional streaming explicitly recorded as implemented or deferred based on verified evidence.
- A working Django application persists conversations/messages in SQLite and supports new chats, provider/model selection from verified availability, prompt/response, saved history, reopening, and context continuation.
- All provider calls are server-side through the verified proxy contract; no unsupported proxy behavior or model availability has been invented.
- Proxy failures, configuration gaps, invalid inputs, and concurrency/retry cases produce safe, understandable outcomes.
- Mocked-proxy tests, live provider smoke requests, Django checks, and migrations pass. Key flows pass locally on port `5001`; the external CodeRange route failure and required platform-route follow-up are clearly documented.
- Living documentation accurately reflects the finished code and contains no secrets.
- The implementation remains on its execution branch until the user explicitly invokes `rendezvous`; this plan phase itself does not create a feature branch or implement application code.

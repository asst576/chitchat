# LiteChat MVP Implementation Plan

- Plan timestamp: `1790658908`
- Plan date: 2026-09-29
- Primary basis: `doc/study/1790658228_litechat_core_functionality_feasibility.md`
- Current repository state at planning: clean `main`; repository contains `AGENTS.md` and the completed study only; no Django application, tests, dependency manifest, canonical docs, or CodeRange config exists.

## OPEN QUESTIONS

These questions affect the proxy integration, data ownership, or deployment. Resolve them during the first execution task. Do not guess an API contract or commit secrets. If the answer is not available from authoritative project/platform documentation, pause the dependent work and request the missing decision/input.

1. **Proxy identity and API contract:** What is the intended LiteChat proxy, and where is authoritative documentation for its base URL, authentication, endpoints, request/response schema, error behavior, limits, and cancellation behavior?
2. **Provider/model availability:** Which of OpenAI, Anthropic, and Google are actually supported by this proxy, and what exact provider/model identifiers are enabled? Does the proxy expose a model catalog endpoint or should the app use a configured allowlist?
3. **Credential ownership/configuration:** Are provider credentials managed by the proxy or supplied to the app as server-side environment variables? What are the required environment-variable names (names only; do not provide secret values)?
4. **App audience and ownership:** Is the initial CodeRange app private and single-user, or must conversations be isolated between authenticated users? Recommended default: private single-user MVP only if CodeRange access is restricted accordingly; otherwise add authentication and per-user ownership before exposing chat history.

Streaming is not an open-question blocker: the implementation must first verify whether the proxy supports it and whether CodeRange can deliver it reliably. If both are confirmed, streaming may be included; otherwise ship a non-streaming response flow.

## Goal

Build a small, secure LiteChat-style application using Django, Python, Django templates, HTML, CSS, JavaScript, and SQLite. Users can start chats, choose an actually available provider/model, send prompts through a verified server-side proxy, receive responses, preserve multi-turn context from stored messages, and reopen saved chat history. The app must be tested through a mocked proxy boundary and verified to start on CodeRange port `5001`.

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
- Validate startup/reachability and expected configuration on CodeRange port `5001`.
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

- [ ] **A1. Verify the LiteChat proxy before writing proxy integration code.** Inspect authoritative docs/config available in the environment and record the proxy base URL configuration key, authentication method, endpoint(s), request/response schema, error/status mapping, provider/model identifier format, provider coverage, enabled model catalog mechanism, request limits/timeouts, and cancellation behavior. Do not make a real request or expose secrets merely to discover the contract.
- [ ] **A2. Resolve the OPEN QUESTIONS.** Confirm which named providers/models are actually supported, whether credentials are shared proxy credentials or provider-specific server environment variables, and whether the deployment is restricted single-user or needs authenticated ownership. If any answer is unavailable, stop the dependent implementation work and request that exact information; do not substitute guessed LiteLLM/OpenAI-compatible behavior.
- [ ] **A3. Record the verified integration decision.** Add a concise implementation note to this plan or a non-secret project doc: confirmed proxy contract source, provider coverage, model-list strategy, environment-variable names only, and whether streaming is supported. Keep all secret values out of the plan and Git.
- [ ] **A4. Decide streaming conditionally.** If the verified proxy supports a documented stream and a CodeRange-compatible server/proxy path can be tested, include SSE as a bounded implementation task. Otherwise use non-streaming responses and record streaming as a limitation. This decision must not delay a working non-streaming MVP.

### B. Django and SQLite Foundation

- [ ] **B1. Inspect available Python/CodeRange runtime constraints** and select a compatible, minimal Django version and outbound HTTP dependency only after checking whether the standard library or an existing dependency is adequate.
- [ ] **B2. Create the Django project and `chat` app** with `manage.py`, settings, root URL configuration, ASGI/WSGI entry points, template/static configuration, and a minimal page route.
- [ ] **B3. Configure runtime settings safely:** SQLite path/default, `DEBUG`, environment-derived `SECRET_KEY`, `ALLOWED_HOSTS`, static settings, and deployment-specific CSRF/HTTPS proxy settings based on verified platform behavior. Do not hardcode production secrets or trust proxy headers without confirmation.
- [ ] **B4. Add dependency and ignore configuration.** Pin or constrain only required runtime dependencies; ignore `.env`, local database files, caches, and generated artifacts. Add an environment example with placeholder values only and confirmed variable names only.
- [ ] **B5. Run baseline Django checks** and confirm a fresh local SQLite database can be created. Record exact commands/results in the execution notes.

### C. Models and Migrations

- [ ] **C1. Implement `Conversation`** with identifier, bounded title, selected provider/model IDs, timestamps, and an owner relation if required by the resolved audience decision.
- [ ] **C2. Implement `Message`** with conversation foreign key/cascade behavior, constrained role, text content, timestamp, deterministic ordering, assistant completion/failure status as required by the chosen send/stream lifecycle, and provider/model attribution for assistant responses.
- [ ] **C3. Add useful indexes and database constraints** for conversation history ordering, message ordering, valid statuses/roles, and per-user filtering if applicable. Keep the schema minimal; do not add a project/interaction abstraction without a demonstrated need.
- [ ] **C4. Generate and review migrations**, then verify a fresh database migrates and tests cover cascade deletion, ordering, timestamps, and model constraints.

### D. Provider Catalog and Secure Proxy Boundary

- [ ] **D1. Implement a server-side provider/model catalog** backed by the verified proxy catalog endpoint or confirmed server-side allowlist. Expose only enabled IDs and safe display labels; never return credentials or arbitrary upstream endpoints.
- [ ] **D2. Add provider/model validation** so all user-submitted selections are checked against currently enabled choices before persistence or proxy calls. Support OpenAI, Anthropic, and Google only where A1/A2 verified availability.
- [ ] **D3. Implement the proxy client against the confirmed contract only.** Load URL/auth from server environment, validate response shape, apply bounded connection/read timeouts and request limits, and map the provider-neutral prompt/context to the exact documented request. Keep provider-specific protocol conversion in this boundary if the proxy does not normalize it.
- [ ] **D4. Keep secrets server-only.** Verify proxy/provider keys are absent from templates, rendered HTML, JavaScript, JSON responses, logs, errors, Git-tracked configuration, and browser storage. Add a safe missing-configuration response.
- [ ] **D5. Add proxy-client tests with mocked HTTP** for successful response, auth/config failure, unsupported model, rate limit, upstream 5xx, malformed body, timeout, and network failure. If streaming is selected, also test framing, end-of-stream, disconnect, and cancellation behavior.

### E. Conversation and Message Flows

- [ ] **E1. Implement recent conversation listing and conversation detail loading** with newest-activity ordering, deterministic message ordering, and ownership filtering where applicable.
- [ ] **E2. Implement new-chat behavior** in a way that does not leave abandoned empty database rows (prefer creating the conversation on first submitted prompt unless the UI requires explicit creation). Initialize it with the selected provider/model.
- [ ] **E3. Implement message submission orchestration.** Validate prompt/provider/model and conversation access; persist the user message before outbound proxy work; build context from ordered successful stored turns plus the new prompt; call the proxy; persist assistant content/status/model attribution on success; update title from a bounded first prompt and conversation activity timestamp.
- [ ] **E4. Handle unsuccessful and incomplete turns.** Preserve the user prompt, mark or report assistant failure safely, exclude failed/partial assistant output from later context by default, and make retry behavior avoid duplicating the user message. Prevent duplicate/in-flight sends as practical for a single-instance SQLite MVP.
- [ ] **E5. Keep multi-turn context stateless at the provider boundary.** Tests must prove prior user/assistant messages are reconstructed from SQLite in the correct order and that historical provider/model attribution remains unchanged if a later turn selects a different supported model.
- [ ] **E6. Add same-origin CSRF-protected views/URLs** for provider choices, history, loading a chat, creating a conversation if needed, and submitting a message. Return stable application-level error categories and appropriate status codes, not raw proxy errors or tracebacks.

### F. Chat Workspace UI

- [ ] **F1. Build the Django-template chat shell** with history navigation, new-chat action, current provider/model controls, message transcript, composer, and clear empty state.
- [ ] **F2. Add responsive CSS** for desktop and mobile, readable user/assistant distinction, long-message wrapping, keyboard focus, and accessible labels/status announcements.
- [ ] **F3. Add JavaScript for new chat, provider/model selection, opening history, prompt submission, and transcript/history refresh** using same-origin endpoints and CSRF tokens. Do not put provider keys or proxy authentication in JavaScript.
- [ ] **F4. Implement loading and failure states:** disable or guard duplicate submit while pending, preserve the prompt on request failure, show a safe retry/actionable message, and distinguish empty history from loading and error states.
- [ ] **F5. Render message content safely.** Use escaped plain text initially. Do not mark model output safe or add unsanitized Markdown/HTML.
- [ ] **F6. If and only if A4 approved streaming, implement browser SSE consumption and incremental UI updates** with complete/failed/cancelled states. Otherwise verify normal response UX and document that responses are non-streaming.

### G. Application Tests and End-to-End Verification

- [ ] **G1. Add model tests** for persistence, stable ordering, cascade deletion, titles/timestamps, roles/statuses, and ownership boundaries if applicable.
- [ ] **G2. Add conversation-service tests** for new chats, prompt persistence, context reconstruction, provider/model validation, failed response exclusion, retry without duplicate prompt, and conversation history updates.
- [ ] **G3. Add Django view tests** for page rendering, new chat/history/reopen flows, message submission, CSRF, invalid input, missing proxy configuration, not-found/unauthorized conversations, and sanitized failures.
- [ ] **G4. Add security regression tests** ensuring secret values never appear in HTML/JSON/errors/log-capture, model output is escaped, arbitrary provider/model/endpoint values are rejected, and cross-user access is denied if accounts are required.
- [ ] **G5. Add mocked-proxy integration tests** that run the Django-to-service-to-SQLite path without live provider credentials, paid requests, or network access.
- [ ] **G6. Run the full test suite, `python manage.py check`, and fresh-database migrations.** Fix implementation-caused issues and record commands/results. Live provider calls must remain optional and explicitly configured.

### H. CodeRange Startup and Validation

- [ ] **H1. Verify CodeRange runtime instructions and configuration** including process command, exposed host/interface, required host/CSRF settings, injected environment-variable names, outbound proxy access, and persistent writable SQLite location. Do not record actual secret values.
- [ ] **H2. Start the application on port `5001`** using the required CodeRange-compatible command and bind address. Identify port conflicts rather than silently changing ports.
- [ ] **H3. Verify reachability and static assets** through the CodeRange endpoint, not only local Django `runserver`.
- [ ] **H4. Exercise key flows on CodeRange:** create a new chat, select an enabled provider/model, submit and receive a response using a mock/stub or explicitly approved configured proxy, reload and reopen history, continue with prior context, and safely display a proxy failure.
- [ ] **H5. If streaming was selected, verify the real CodeRange serving/reverse-proxy path** does not buffer or prematurely terminate SSE and that disconnects close upstream work when supported.
- [ ] **H6. Verify SQLite persistence across the expected restart lifecycle** or document if CodeRange storage is ephemeral and requires a persistent volume/configuration change.

### I. Documentation

- [ ] **I1. Add living setup/overview documentation under `doc/wiki/`** covering only implemented features, supported provider/model discovery, Python dependency installation, migrations, startup, and tests.
- [ ] **I2. Document the actual proxy integration contract at a safe level** including endpoint semantics, confirmed environment-variable names, request flow, supported provider/model subset, streaming behavior, and safe placeholder values. Never include real credentials or undocumented guesses.
- [ ] **I3. Add a CodeRange/setup footgun document under `doc/wiki/footguns/`** for port `5001`, required injected configuration, SQLite persistence, host/CSRF/reverse-proxy settings, and common startup/proxy failures actually encountered.
- [ ] **I4. Document known limitations** such as non-streaming behavior when selected, text-only messages, no user accounts if approved private single-user use, no automatic context compaction, and unsupported providers/models. Do not describe out-of-scope features as implemented.
- [ ] **I5. Review all docs against the actual code after implementation** and commit docs with the implementation work as focused changes; do not rewrite the historical study.

## Testing

The default test suite must be offline and must mock the proxy boundary. It should cover models/migrations, context order, provider catalog/validation, all message send outcomes, endpoint authorization/CSRF, safe errors, and secret non-disclosure. No real provider credentials or paid API calls should be required to run tests. Conditional stream behavior gets its own mocked chunk/cancellation tests and a separate CodeRange smoke check.

## Validation

- `python manage.py check` passes with the documented test/development environment.
- Fresh SQLite database migrations apply successfully; tests pass against an isolated test database.
- Provider/model choices match only the verified proxy catalog/allowlist and all outbound calls use the server-side proxy client.
- New chat, prompt/response, saved history, reopen, and context continuation work with a mocked proxy; unsupported selection and upstream failure paths are safe.
- Credentials do not appear in browser output or tracked files.
- The application starts and is reachable on CodeRange port `5001`, with static assets and database persistence behavior verified.
- If streaming is absent or impractical, the UI uses non-streaming requests and documentation explicitly records the limitation.

## Documentation Updates

Update only living documentation under `doc/wiki/` and `doc/wiki/footguns/` as part of execution. Suggested files are `doc/wiki/overview.md`, `doc/wiki/setup.md`, `doc/wiki/architecture.md`, and `doc/wiki/footguns/coderange-and-proxy.md`. Exact filenames may be consolidated if that keeps the documentation concise. Include actual environment-variable names with placeholders, provider/model availability, database/migration setup, tests, CodeRange startup/reachability, and known limitations. Leave the study as a historical artifact.

## Completion Criteria

- All applicable implementation and documentation checklist items are completed, with conditional streaming explicitly recorded as implemented or deferred based on verified evidence.
- A working Django application persists conversations/messages in SQLite and supports new chats, provider/model selection from verified availability, prompt/response, saved history, reopening, and context continuation.
- All provider calls are server-side through the verified proxy contract; no unsupported proxy behavior or model availability has been invented.
- Proxy failures, configuration gaps, invalid inputs, and concurrency/retry cases produce safe, understandable outcomes.
- Mocked-proxy tests pass, Django checks and migrations pass, and the key flows are verified on CodeRange port `5001` or any platform-specific blocker is clearly documented with required human follow-up.
- Living documentation accurately reflects the finished code and contains no secrets.
- The implementation remains on its execution branch until the user explicitly invokes `rendezvous`; this plan phase itself does not create a feature branch or implement application code.

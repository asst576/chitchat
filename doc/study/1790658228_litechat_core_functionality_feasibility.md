# LiteChat Core Functionality and Recreation Feasibility

- Study timestamp: `1790658228`
- Study date: 2026-09-29
- Repository path: `/home/coder/litechat`
- Git status before changes: `fatal: not a git repository (or any of the parent directories): .git`

## Executive Summary

A focused LiteChat-style chat application is feasible with Django, HTML, CSS, JavaScript, and SQLite. The core experience is a durable chat workspace: start a conversation, choose a provider/model, exchange messages with the selected model, retain prior turns as context, and return to saved conversations from history.

This directory currently contains only `AGENTS.md`; there is no application code or Git metadata to inspect. The public open-source project at `github.com/DimitriGilbert/LiteChat` is a useful feature and UX reference, but its architecture differs materially from this project's intended stack: it describes a client-side React application storing data in browser IndexedDB and connecting to provider APIs. Its public documentation does not establish a server-side product called the “LiteChat proxy API.” Other, unrelated products also use the LiteChat name. Therefore, the intended proxy's URL, authentication, request/response format, provider routing, model catalog, streaming support, and credential ownership are unknown and must not be guessed.

The recommended first release is deliberately narrower than the public LiteChat app: one chat workspace, a server-provided allowlist of configured providers/models, prompt submission and assistant replies, durable conversation/message history, reopening conversations, multi-turn context, and clear safe failure states. Do not start with projects, agents, tools, MCP, file uploads, web search, workflows, plugins/mods, model races, Git sync, multimodal content, or import/export. Streaming is desirable to match contemporary chat UX, but its MVP status depends on whether the intended proxy supports it and CodeRange can serve it reliably.

## Scope and Method

This study combines the project context in `AGENTS.md`, the current workspace state, public LiteChat project documentation, Django security documentation, and available public provider/proxy documentation. It is a feasibility study, not a specification of an undocumented API.

## Current Repository State

### Confirmed facts

- The workspace contains `AGENTS.md` and no application source, Django project, tests, dependency manifest, migrations, settings, or canonical project documents.
- `git status` fails because `/home/coder/litechat` is not inside a Git repository. This prevents making the Conventional Commit required by the project workflow unless Git metadata becomes available. Initializing a new Git repository would be a separate, unrequested repository change and was not done.
- The project's approved direction is Django, Python, HTML, CSS, JavaScript, SQLite, and an intended LiteChat proxy API. The eventual CodeRange port is `5001`.
- OpenAI, Anthropic, and Google are likely target providers. Exact enabled models and API credentials are not confirmed.

### Public LiteChat reference and product-name ambiguity

The public repository `DimitriGilbert/LiteChat` describes LiteChat as a local-first, modular AI chat app. Its README and developer docs describe multiple providers, model selection, streaming, saved conversations, and extensive optional functionality. Its persistence documentation uses IndexedDB/Dexie for conversations, interactions, projects, provider configuration, and settings. Its AI integration documentation describes provider adapters in the browser and a Vercel AI SDK-based service layer. The README says data is client-side and provider requests are made from the browser; it does not describe this project's intended Django proxy service.

The public `litechat.ai` site is a separate product/site and advertises OpenAI and Anthropic model access, attachments, web search, and saved/renamable sessions. Those claims are not sufficient evidence that it is the intended reference or that those optional features belong in this project's MVP. Search results also surfaced other unrelated LiteChat-branded applications.

**Interpretation used here:** use the open-source LiteChat project as a broad product/UX reference and use the explicit requirements in this project's `AGENTS.md` as the implementation direction. Do not reproduce LiteChat's React, browser key storage, IndexedDB persistence, or extensive feature set. Confirm product identity and the intended proxy during planning before treating any public product's details as binding requirements.

## Core User Experience

The minimum coherent chat loop should feel like one persistent workspace:

1. The user opens a chat page with a conversation-history area and a clear new-chat action. With no chats, show an empty state and a prompt to begin.
2. The user selects an enabled provider and model from choices the server actually supports. Model selection should be understandable as a pair (provider, model), not an ambiguous display label.
3. The user enters a prompt and submits it. The interface indicates that a response is pending, prevents accidental duplicate submissions, and keeps the current transcript visible.
4. The assistant reply appears in the transcript. Streaming text is a strong UX improvement when supported; a non-streaming answer is an acceptable first functional milestone if streaming support is unknown or unreliable.
5. The user's prompt and successful assistant reply are saved. A later turn sends the prior eligible turns plus the new prompt, so the assistant can respond with conversation context.
6. The history list reflects recent activity. Selecting an entry reopens its transcript, model/provider context, and ability to continue.
7. Failures are shown in the relevant conversation without presenting server traces, proxy credentials, or opaque upstream internals to the browser.

The important perceived qualities are low-friction prompting, an obvious model choice, readable role-separated messages, visible pending/error states, and confidence that the conversation can be resumed. Advanced organization and power-user tools are not needed to deliver that loop.

## MVP Feature Assessment

| Capability | MVP assessment | Notes |
|---|---|---|
| Create a new conversation | Essential | Can create lazily on first prompt or explicitly with a new-chat action; avoid leaving unusable empty records. |
| Select provider and model | Essential | Offer only server-configured, enabled combinations. Persist the selected pair so a reopened chat is understandable. |
| Submit prompts and show replies | Essential | Validate non-empty input and set practical request-size limits. |
| Multi-turn context | Essential | Rebuild provider context from ordered persisted messages for each request. |
| Save conversations and messages | Essential | Persistence is necessary for returning to history and continuing chats. |
| View/reopen chat history | Essential | Sort by most recently updated and load only the selected transcript. |
| Loading, empty, and error states | Essential | Prevent duplicate sends and make provider failures recoverable. |
| Streaming output | Recommended, conditional | Matches modern chat expectations and the public reference, but requires proxy stream-contract and deployment verification. Non-streaming can unblock the first working version. |
| Conversation rename/delete | Useful, not foundational | Rename can be a local title edit; deletion requires explicit confirmation and cascading message deletion. Confirm if considered part of MVP. |
| Automatic AI-generated titles | Defer | A truncated first prompt is adequate initially and avoids an extra model call/cost. |
| Markdown/code block rendering | Defer or constrain | Plain escaped text is safest initially. If Markdown is added, sanitize rendered HTML and test XSS cases. |
| Attachments, images, multimodal input | Out of scope | Requires content-part storage, upload limits, provider capability differences, and proxy contract support. |
| Web search/browsing | Out of scope | Requires a separate search/tool execution contract and user-facing sourcing behavior. |
| Tools, agents, MCP, workflows, prompt library/rules | Out of scope | These are advanced LiteChat capabilities with large security and product surface areas. |
| Projects, nested organization, tags | Out of scope | Basic history is sufficient for a single-user MVP. |
| Compare/race multiple models, regenerate-with-model | Out of scope | Adds concurrent provider calls, response grouping, and cost controls. |
| Conversation sync, export/import, plugins/mods, virtual filesystem, Git integration | Out of scope | Not required for core chat and significantly expands security and data-management work. |

## Feasibility and Recommended Architecture

The intended stack is adequate for the MVP. Django can render a server-owned application shell, validate requests, persist relational data, enforce CSRF, and make outbound proxy requests. Small amounts of browser JavaScript can submit messages asynchronously, update pending/error UI, render new transcript items, and optionally consume Server-Sent Events (SSE). SQLite is adequate for a low-volume, single-instance MVP and straightforward local development.

Recommended request flow:

`Browser (same-origin HTML/CSS/JS) -> Django URL/view -> chat/provider service -> configured LiteChat proxy -> selected upstream provider/model`

For reads, Django loads owned/available conversations and their messages from SQLite. The browser should not call the proxy directly. A server-side service boundary should isolate proxy-specific details so provider routing, upstream serialization, timeout handling, and stream parsing do not become mixed into templates or view logic.

Suggested responsibility boundaries:

- **Templates/static assets:** application shell, history navigation, message transcript, provider/model selectors, composer, accessible loading/error states.
- **URLs/views:** HTML page and narrowly scoped JSON endpoints for listing/creating/opening/updating/deleting conversations and submitting a message. Views validate HTTP input, enforce ownership/CSRF, call services, and return stable application-level responses.
- **Conversation service:** validate prompt and selection, construct ordered context, persist user/assistant messages and conversation timestamps, and coordinate failures/retries.
- **Proxy client/provider adapter:** read server configuration, construct the proxy request, map provider/model identity, enforce timeouts, parse normal or streaming results, and translate upstream failures to a small safe error taxonomy.
- **Django ORM/SQLite:** conversation and message records, relationships, timestamps, order, and migrations.

An initial implementation can use Django's built-in session/CSRF mechanisms and vanilla JavaScript. A separate frontend framework, task queue, Redis, vector database, and provider SDKs are not necessary unless the verified proxy contract requires them.

## LiteChat Proxy Placement and Contract

The proxy should sit between Django and provider APIs, not between browser JavaScript and the providers. This keeps provider credentials out of HTML, JavaScript bundles, browser storage, and browser network calls; provides one controlled outbound boundary; and allows a stable internal interface even when provider APIs differ.

The proxy's exact identity and contract are currently **unknown**. The public open-source LiteChat documentation reviewed here describes direct browser-to-provider integration and does not verify a server-side “LiteChat proxy API.” “LiteChat proxy” may refer to an environment/platform service not documented in this workspace, or to a different service. Do not assume that it is LiteLLM or that it accepts OpenAI-compatible request shapes.

Before implementation, verify at minimum:

- Base URL, environment-variable names, and whether the proxy is reachable from CodeRange's server process.
- Authentication method and which party owns the upstream OpenAI, Anthropic, and Google credentials.
- Supported request endpoint(s), provider/model identifier format, message schema, system-prompt handling, and generation settings.
- Whether it exposes a model-catalog endpoint or requires a configured local allowlist.
- Whether it streams, the wire format (for example SSE), cancellation behavior, and how errors are reported.
- Limits, timeouts, rate limits, logging/data-retention behavior, and whether it forwards upstream status codes or wraps them.

Keep the proxy base URL and credentials in server environment/configuration, never request-controlled URLs. Do not return proxy auth headers or keys to the browser. If the proxy uses one server credential, expose only models actually allowed by that credential. If each end user supplies provider keys, that is a separate security/storage requirement and must be decided explicitly; plaintext browser/localStorage storage is not acceptable for this server-rendered app.

## Provider and Model Selection

The UI should get its choices from a Django endpoint or server-rendered configuration derived from an explicit allowlist or a verified proxy catalog. Use stable provider IDs (`openai`, `anthropic`, `google`) and exact model IDs as data, with human-readable labels separate from IDs. Filter models when the provider changes. Validate every submitted provider/model pair server-side; never trust hidden form fields or a browser-supplied arbitrary endpoint.

For a minimal deployment, a small server-side configured catalog is safer and more predictable than assuming arbitrary model discovery. If the proxy has a supported model-list endpoint, it can populate/refresh that catalog with caching and safe failure behavior. Keep dynamic discovery out of the browser unless the proxy explicitly requires it.

Provider APIs are not interchangeable at the wire level. OpenAI chat-style APIs represent turns as role/content messages; Anthropic's Messages API accepts alternating user/assistant messages and has a top-level `system` field rather than a system role in the message list; Google Gemini's API has its own content/role and system-instruction representation. A proxy may normalize these differences, but this must be confirmed. Keep the internal domain format provider-neutral (ordered role/content turns plus selected provider/model and optional system instruction) and let the proxy adapter handle the verified wire format. Avoid pretending every setting, tool, attachment, or stream event has identical semantics across providers.

Do not hardcode a long catalog of model names from web pages: available IDs, aliases, retirement dates, account entitlements, and proxy allowlists change. The proxy/catalog contract is the source of truth. At conversation creation, save the selected provider and model; at each assistant response, save the actual provider/model used so later model changes do not rewrite historical attribution.

## Data Model Study

Two principal Django models should cover the minimum requirements:

### `Conversation`

- UUID or integer primary key.
- Title, initially generated from a bounded/truncated first user prompt or a neutral default.
- Selected provider ID and model ID for the conversation's current/default selection.
- Created and updated timestamps; `updated_at` should change on successful prompt activity so history sorts correctly.
- Optional owner/user foreign key if this is multi-user or exposed beyond a trusted single-user environment. Authentication/ownership is not confirmed and must be decided before a shared deployment.

### `Message`

- Primary key and foreign key to `Conversation` with cascade deletion.
- Role (`user` or `assistant` in the first MVP; do not accept arbitrary roles from the browser).
- Text content.
- Stable ordering field or deterministic `(created_at, primary key)` ordering within the conversation.
- Created timestamp.
- Status for in-progress/completed/failed assistant responses if streaming or retry behavior needs durable state.
- Provider/model snapshot on the assistant message or interaction if model changes can happen within a conversation.
- Optional safe error category/status separate from user-visible message text.

If the UI needs metadata about one user submission plus its assistant response, a later `Turn`/`Interaction` model can group those messages. It is not required for the smallest MVP. Avoid storing binary uploads in message text. Attachments would need a separate content/file design and are out of scope.

Index messages by conversation and deterministic order; index conversations by updated time (and owner plus updated time if ownership applies). Deleting a conversation should cascade to its messages. SQLite migrations are required before a new database can run the app.

## Conversation Context and Persistence Behavior

Conversation history in the database is the canonical record. On a new turn, Django should load the conversation's successful, context-eligible messages in order and append the new user message before calling the proxy. Send the provider-neutral conversation context plus the current selected provider/model to the server-side proxy client. On success, persist the assistant response and update the conversation timestamp/title. This remains stateless between provider calls and does not depend on an upstream provider retaining conversation state.

Persisting the user prompt before the outbound call preserves user work if the proxy fails. The UI should distinguish a failed turn from a completed assistant response and allow a deliberate retry without silently duplicating the user message. For streaming, create/update an assistant message as chunks arrive and mark it completed or failed at stream termination. Avoid recording an empty assistant reply as success.

Do not include failed/incomplete assistant output in future context by default. Keep context ordering deterministic. A first MVP can send the full bounded transcript; long conversations will eventually exceed provider context windows or proxy limits. Until truncation/summarization is designed, set request size limits, surface a clear context-too-large error, and do not silently drop older turns. Token estimation and summarization are follow-up design topics.

## Likely Django Areas (Illustrative, Not Existing Files)

No Django files currently exist. A likely small project layout is:

- `manage.py`, project package settings/ASGI/WSGI/root URLs.
- One `chat` app with `models.py`, `views.py`, `urls.py`, `forms.py` or request validators, and migrations.
- `chat/services/conversations.py` for persistence/context orchestration.
- `chat/services/proxy_client.py` (or a provider adapter module) for outbound proxy integration.
- `templates/chat/` for the page and message/history partials.
- `static/chat/` for focused CSS and JavaScript.
- Django tests alongside the app, including model, view, service, and request tests.

Likely URL surface, subject to plan and UI decisions:

- `GET /` renders the chat workspace.
- `GET /api/providers/` returns enabled provider/model choices.
- `GET /api/conversations/` lists history.
- `POST /api/conversations/` creates a conversation if explicit creation is used.
- `GET /api/conversations/<id>/` loads a conversation and ordered messages.
- `PATCH /api/conversations/<id>/` updates fields such as title or selected model if supported.
- `DELETE /api/conversations/<id>/` deletes it if deletion is in scope.
- `POST /api/conversations/<id>/messages/` submits a prompt and returns a response or starts a stream.

These are candidate boundaries, not a commitment to a specific URL schema. Do not add a general-purpose public API layer where ordinary Django views are enough.

## Security Considerations

- Keep all provider/proxy credentials server-side in environment variables or a managed secret store. The example names in project context (`LITECHAT_OPENAI_KEY`, `LITECHAT_ANTHROPIC_KEY`, `LITECHAT_GOOGLE_KEY`) are plausible names, not verified runtime configuration. Do not add real values or `.env` to Git.
- Do not render credentials into templates, JavaScript configuration, API responses, logs, error text, or browser storage.
- If the proxy owns provider keys, Django may only need a proxy service credential; confirm its scope and rotation process. If users own keys, require an explicit encrypted server-side key design and access-control policy before implementation.
- Keep same-origin write endpoints CSRF-protected. Do not apply blanket `csrf_exempt` to the chat endpoints.
- Decide whether the app is a single-user local/CodeRange tool or multi-user. For multiple users, require authentication and filter every conversation/message lookup by owner to prevent insecure direct object reference (IDOR). A guessed UUID is not authorization.
- Validate role, prompt length, provider/model allowlist, conversation ownership, and request content type. Do not accept arbitrary proxy URLs from clients (SSRF risk).
- Treat prompts, model output, and titles as untrusted data. Preserve Django template autoescaping; if adding Markdown/HTML rendering, sanitize with a narrow allowlist before using safe HTML.
- Configure `DEBUG=False`, a strong uncommitted `SECRET_KEY`, `ALLOWED_HOSTS`, HTTPS/proxy settings, secure cookies, and CSRF trusted origins appropriately outside development. Do not infer reverse-proxy headers without verifying CodeRange's behavior.
- Avoid logging full prompts, completions, credentials, or authorization headers by default. Restrict request/body size and consider abuse/cost controls if the app is reachable by multiple users.

Django supplies useful defaults for CSRF, template escaping, and parameterized ORM queries, but deployment configuration and correct use remain necessary. These points follow Django's security guidance; they do not replace a deployment-specific review.

## Error Handling and Failure Cases

| Failure | Server behavior | User experience |
|---|---|---|
| Missing proxy configuration/credential | Detect at startup or before request; return safe service-unavailable/configuration category; never leak the value | Explain that AI service is not configured; preserve prompt/history |
| Invalid/missing provider key at upstream | Map to an authentication/configuration error; redact upstream body/headers | Show actionable but non-sensitive message; do not loop retries |
| Unsupported/disabled model | Reject before proxy call using configured catalog | Ask user to choose an enabled model |
| Proxy/provider rate limit | Map rate limit; preserve retry metadata only if safe | Tell user to wait/retry; prevent automatic repeated paid calls |
| Network failure or timeout | Bound connect/read/overall timeouts; mark turn failed; log correlation ID and safe category | Preserve the prompt and offer retry |
| Proxy 5xx or malformed response | Validate response shape; treat as upstream failure | Show generic response failure, not traceback/raw proxy payload |
| Context or request too large | Apply request limits and map known provider/proxy size errors | Ask user to shorten/start a new chat; do not silently truncate |
| Stream disconnect/cancel | Mark partial response explicitly; close upstream connection when possible | Show interruption and provide controlled retry/cancel behavior |
| Database failure while saving | Use transactions around related state changes; distinguish provider success from persistence failure | Warn that the response could not be saved; avoid claiming durability |
| Concurrent/duplicate submissions | Disable submit while pending and/or use a request/turn idempotency strategy | Avoid duplicated prompts, charges, and confusing ordering |

Public errors should use stable application-level categories. Detailed diagnostics belong in redacted server logs, correlated by a request ID. Do not retry paid provider operations automatically unless the proxy contract guarantees safe idempotency.

## Testing Strategy

- **Model tests:** create conversations/messages, cascade deletion, deterministic ordering, timestamp updates, validation and any uniqueness constraints.
- **Context tests:** verify the exact ordered turns sent to a mocked proxy, successful prior assistant replies included, failed/incomplete replies excluded, provider/model selection passed through, and switching the selected model does not change historical message attribution.
- **Proxy-client unit tests:** mock HTTP responses for success, invalid JSON, 401/403, 404/unsupported model, 429, 5xx, timeout, network error, and (if implemented) SSE chunks, stream completion, cancellation, and disconnect.
- **View tests:** page and history rendering, valid/invalid message submission, CSRF behavior, status/error mapping, disabled model rejection, conversation not-found/ownership isolation, and rename/delete if included.
- **Security tests:** ensure secrets never appear in rendered HTML/API JSON, user-controlled provider/model cannot select arbitrary endpoints, templates escape model output, and one user's conversation cannot be accessed by another if auth exists.
- **Integration tests:** run full Django-to-mocked-proxy-to-SQLite flow without live provider credentials or paid calls; verify created message history and reopening/context continuity.
- **Browser/CodeRange smoke tests:** new chat, choose model, submit prompt, receive reply from a stub/test proxy or approved credentialed environment, reload, reopen, continue with prior context, and exercise a failed-proxy path. Do not claim provider integration works from mocked tests alone.
- Run Django system checks and migrations as applicable, and verify the actual serving stack's stream behavior if streaming is part of the implementation.

Keep provider/network tests deterministic and offline by mocking the proxy boundary. Live provider tests should be optional, explicit, and never required for the default test suite.

## CodeRange and Port 5001

The repository does not currently contain CodeRange configuration, dependencies, or a runnable app, so deployment compatibility cannot be verified in this study. During execution/rendezvous, verify rather than assume:

- The Django server binds to `0.0.0.0:5001` (or the platform's required interface/command), and port 5001 is not already occupied.
- Required Python/Django/http client dependencies install in the environment and startup configuration is available.
- `ALLOWED_HOSTS`, CSRF trusted origins, and forwarded HTTPS/proxy settings match the platform's actual hostname and TLS termination.
- Proxy DNS/network access and server-side credentials are present without exposing them to the browser.
- SQLite's path is writable and persists across restarts if conversation retention is expected; container/ephemeral storage can otherwise erase history.
- Static assets are served correctly in the deployment mode.
- If streaming is used, the ASGI/WSGI server and any reverse proxy do not buffer or prematurely time out SSE responses. A synchronous WSGI stream can occupy a worker for the duration of a completion; test real worker limits and concurrency. Non-streaming is operationally simpler.

Local `runserver` success alone is not proof of CodeRange deployment correctness or reachability.

## Dependencies and Tradeoffs

- Django and SQLite provide routing, ORM, migrations, templates, security middleware, and durable relational storage without requiring a separate JavaScript framework or database service.
- A small HTTP client library may be needed for outbound proxy calls if not already present; select only after the real proxy contract and streaming needs are known.
- For streaming, Django's `StreamingHttpResponse` can carry SSE, but production server/proxy behavior and concurrency characteristics must be tested. ASGI may be preferable for long-lived asynchronous streams; whether CodeRange supports the chosen server is unknown.
- Keeping a stable provider-neutral domain request simplifies the chat service, while translating provider differences adds adapter work at the proxy boundary. The system must not assume the proxy performs this normalization unless documented.
- SQLite is easy to deploy and sufficient for the likely first milestone but is less appropriate for high write concurrency, horizontally scaled app instances, or shared network storage. Revisit only if usage/deployment requires it.
- Server-owned keys protect secrets from visitors but make the application operator responsible for access, spend, rate limits, and privacy. Per-user keys avoid central provider spend but require authenticated encrypted key storage and lifecycle/security work.

## Risks, Assumptions, and Unknowns

### Confirmed facts

- The intended stack, likely provider set, broad chat/history goals, secret-handling restriction, and CodeRange port come from the project instructions.
- The current workspace has no implementation to extend and is not currently a Git repository.
- The public open-source LiteChat reference documents a significantly more feature-rich client-side architecture than this project intends.

### Assumptions used for recommendations

- The first release should prioritize a single conversation workspace and a small configured model catalog over parity with every public LiteChat feature.
- Server-side proxy calls are intended because project context explicitly mentions a proxy API and requires secrets not be exposed in frontend code.
- The initial data model can be text-only and does not require attachments or multimodal content.
- A first release can use a single Django deployment and SQLite with low/modest concurrency.

### Material unknowns and risks

- Which LiteChat product/source defines the expected user experience?
- What is the actual proxy service, its endpoint/base URL, credentials, wire schema, model catalog, and provider routing behavior?
- Does the proxy expose OpenAI, Anthropic, Google-specific or normalized APIs? Does it support SSE and cancellation?
- Are keys centrally provisioned to the proxy or supplied per user? Who pays for usage and how will abuse/cost be limited?
- Is the app single-user/private or multi-user/public? This determines whether authentication and per-user ownership are MVP-critical.
- Which model IDs are enabled for this account/proxy, and how are they maintained as models change?
- Is streaming required, or is a complete response after generation acceptable for the first usable release?
- What host/domain, persistent volume, startup command, and reverse-proxy behavior does CodeRange provide?
- There is no Git repository metadata, so the study cannot currently be committed as required by `AGENTS.md` without a repository-level setup decision.

## Recommended MVP Scope

1. One responsive chat page with a history sidebar/list, transcript, new-chat affordance, provider/model selector, composer, and accessible pending/empty/error states.
2. Server-authoritative provider/model choices from a verified configured allowlist or proxy catalog.
3. Django conversation and message persistence in SQLite with migrations and deterministic turn ordering.
4. Server-side provider/proxy client with bounded timeouts, input validation, safe error translation, and no browser-visible secrets.
5. Multi-turn context reconstructed from saved successful messages; persist user prompt before external call and persist assistant completion/error status consistently.
6. History list, reopen, and continue behavior; sort by recent activity. Keep rename/delete decisions small and explicit.
7. Default tests using a mocked proxy, plus CodeRange startup/reachability and important-flow verification on port `5001` during execution/rendezvous.
8. Add streaming only after confirming proxy support and deployment behavior; otherwise make non-streaming delivery clear and preserve the same service boundary for later streaming work.

## Explicitly Out of Scope for the First MVP

Projects and nested workspaces; multimodal/file uploads; real-time web search; tool execution, agents, MCP, or workflows; prompt libraries/rules/tags; model races/comparison; automatic AI title generation; regenerate/edit assistant responses; conversation Git synchronization; plugins/mods; virtual filesystem; data import/export; custom themes; billing dashboards; provider-side fine-tuning; and multiple storage backends. These are present in or associated with some LiteChat-branded products but are not required by the confirmed project context.

## External Sources Reviewed

Reviewed 2026-09-29. Public product documentation can change and does not define this project's hidden proxy contract.

- Open-source LiteChat repository/README: <https://github.com/DimitriGilbert/LiteChat>
- LiteChat developer guide: <https://raw.githubusercontent.com/DimitriGilbert/LiteChat/main/docs/readme.md>
- LiteChat AI integration: <https://raw.githubusercontent.com/DimitriGilbert/LiteChat/main/docs/ai-integration.md>
- LiteChat persistence: <https://raw.githubusercontent.com/DimitriGilbert/LiteChat/main/docs/persistence.md>
- LiteChat service layer: <https://raw.githubusercontent.com/DimitriGilbert/LiteChat/main/docs/services.md>
- LiteChat API reference: <https://raw.githubusercontent.com/DimitriGilbert/LiteChat/main/docs/api-reference.md>
- Separate LiteChat-branded site reviewed for name ambiguity: <https://litechat.ai>
- Django security guidance: <https://docs.djangoproject.com/en/stable/topics/security/>
- Anthropic Messages API reference (message list/system prompt distinctions): <https://docs.anthropic.com/en/api/messages>
- LiteLLM proxy docs reviewed as an example of a distinct gateway product, not as evidence that this project uses it: <https://docs.litellm.ai/docs/simple_proxy>

OpenAI and Google documentation URLs were attempted but could not be reliably retrieved by the research tool in this session. Their exact proxy/API integration remains unverified and should be confirmed against the selected proxy's own documentation before implementation.

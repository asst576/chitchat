# Architecture

## Request Flow

Browser templates, CSS, and JavaScript make same-origin requests to Django. Django validates inputs and conversation state, reconstructs context from SQLite, then calls `https://proxy.litechat.ai` from the server. Provider keys are attached only to that server-side request.

```text
Browser -> Django views -> conversation service -> provider-specific proxy client -> BUILD LLM Proxy
                                      |                                |
                                      +---------- SQLite ---------------+
```

There is no browser-to-provider request and no direct database access from JavaScript.

## Reverse-Proxy Subpath

CodeRange mounts the workspace below `/proxy/5001/`. The page declares `<base href="./">` and uses relative CSS/JavaScript references so the browser keeps requests below that mount. For example, assets resolve to `/proxy/5001/static/chat/chat.css` and `/proxy/5001/static/chat/chat.js`. JavaScript builds its API root from `document.baseURI`, producing `/proxy/5001/api`. Django retains `STATIC_URL = "/static/"` and serves files from `STATICFILES_DIRS`. The CodeRange proxy must remove `/proxy/5001` before forwarding requests so Django receives `/static/...` and `/api/...`; local checks simulated this mapping, but post-fix browser delivery was not independently verified in this session.

## Django Areas

- `config/settings.py`: Django, SQLite, environment settings, templates, and static files.
- `config/urls.py`: chat page, health endpoint, and API routes.
- `chat/models.py`: `Conversation` and `Message` persistence.
- `chat/providers.py`: fixed, documented provider/model allowlist and server-side key-presence status.
- `chat/services/conversations.py`: input validation, lazy conversation creation, ordered context reconstruction, pending/failed turn state, completion persistence, and explicit retry.
- `chat/services/proxy_client.py`: verified provider-specific URL, header, request-body, response-body, and failure mapping.
- `chat/views.py` and `chat/urls.py`: same-origin JSON endpoints with Django CSRF middleware.
- `templates/chat/index.html` and `static/chat/`: responsive workspace and DOM updates. Model output is inserted as text, not HTML.

## Persistence and Context

`Conversation` stores title, current provider/model selection, and timestamps. `Message` stores role, text content, status, provider/model attribution for assistant turns, and a safe failure category. Deleting a conversation through the ORM cascades to its messages; no delete UI/API is currently exposed.

New conversations are created lazily on the first prompt. The app stores that prompt and creates a pending assistant message before calling the proxy. On success, the assistant message becomes completed. On proxy failure, the prompt is retained and the assistant message is marked failed. A retry targets the latest failed assistant message and reuses its preceding user prompt.

Context construction includes only completed user/assistant pairs plus the current user prompt. Failed and incomplete turns are excluded. The entire eligible history is sent each time; token-window compaction is not implemented.

## Proxy Contract

The proxy's public docs (revision 2026-09-19) document separate formats rather than one normalized endpoint:

| Interface | Endpoint | Authentication | Allowlisted model |
|---|---|---|---|
| OpenAI Chat Completions | `POST /openai/v1/chat/completions` | `Authorization: Bearer` using `BUILD_OPENAI_KEY` | `gpt-5.6-luna` |
| Anthropic Messages | `POST /anthropic/v1/messages` | `x-api-key` using `BUILD_ANTHROPIC_KEY`, plus `anthropic-version: 2023-06-01` | `claude-haiku-4-5-20251001` |
| Google Gemini Generate Content | `POST /google/v1beta/models/gemini-3.8-flash:generateContent` | `x-goog-api-key` using `BUILD_GOOGLE_KEY` | `gemini-3.8-flash` |

The app maps the same internal ordered text turns to each documented request shape and parses each response separately. No model discovery endpoint was found in the proxy docs; the initial model choices are a static allowlist. The proxy says all three interfaces currently use DeepSeek Flash, so these names are interface/model identifiers and do not indicate three distinct upstream model implementations.

The app uses non-streaming requests with a 90-second timeout and a 2,000,000-byte response limit. It makes no automatic retry after an upstream failure. Proxy statuses are mapped to safe app errors; raw upstream bodies, headers, and keys are not returned to the browser.

Source: <https://proxy.litechat.ai/docs>, <https://proxy.litechat.ai/docs/openai/chat-completions>, <https://proxy.litechat.ai/docs/anthropic/messages>, <https://proxy.litechat.ai/docs/google/gemini>.

## Privacy Boundary

This is a private single-user app with no built-in authentication or user ownership fields. Every conversation in the SQLite database is visible to anyone who can reach this app. It must be deployed behind private access control. CodeRange's actual access-control and TLS/reverse-proxy behavior has not yet been verified.

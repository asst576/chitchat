# Architecture

## Request Flow

The browser loads Django templates and local CSS/JavaScript. Authenticated same-origin views scope every conversation operation to `request.user`; the conversation service reconstructs context from SQLite and calls `https://proxy.litechat.ai` server-side. Provider keys are attached only to that request.

```text
Browser -> Django auth/session -> owner-scoped views -> conversation service -> provider client -> proxy
                                      |                         |                  |
                                      +---- User/Profile/Billing +---- SQLite -----+
```

There is no browser-to-provider request or direct database access from JavaScript. Signup atomically creates the Django user, `UserProfile`, and `BillingAccount`.

## Authentication and Ownership

The project uses Django's default `auth.User`, password validators, database-backed sessions, CSRF middleware, and explicit login checks. HTML views redirect to `/accounts/login/`; JSON APIs return a JSON 401. Signup and login are public endpoints, logout is POST-only, and the workspace, profile, billing, and chat APIs require authentication.

`Conversation.owner` is a required, protected foreign key in the final schema. List, detail, continue, and retry operations filter by the current user. A foreign conversation UUID is indistinguishable from an unknown UUID at the API boundary. New conversations always receive the authenticated request user; submitted owner IDs are ignored.

Legacy databases use staged migrations. Migration `0003` adds a nullable owner during the transition. `provision_bootstrap_account --username BOOTSTRAP_USERNAME` creates the bootstrap user's profile and billing account; `assign_legacy_conversation_owner --username BOOTSTRAP_USERNAME` explicitly assigns unowned rows. Migration `0004` refuses to apply while any unowned conversation remains, then enforces NOT NULL. Back up and rehearse an existing database before this sequence; see [Setup](setup.md).

## HTTP Surface

These are Django's upstream paths; the CodeRange proxy exposes them below `/proxy/5001/`.

| Path | Methods | Access |
|---|---|---|
| `/` | GET | Authenticated chat workspace |
| `/accounts/signup/` | GET, POST | Public only when signup is enabled and bootstrap/ownership gates pass; otherwise 404 |
| `/accounts/login/` | GET, POST | Public |
| `/accounts/logout/` | POST | CSRF-protected session logout |
| `/profile/` | GET, POST | Authenticated current-user profile |
| `/billing/` | GET | Authenticated, read-only current-user billing account |
| `/healthz/` | GET | Public health status |
| `/api/providers/`, `/api/conversations/` | GET | Authenticated |
| `/api/conversations/<uuid>/` | GET | Authenticated owner; foreign/unknown UUID returns 404 |
| `/api/messages/` | POST | Authenticated conversation creation |
| `/api/conversations/<uuid>/messages/`, `/api/conversations/<uuid>/retry/` | POST | Authenticated owner; foreign/unknown UUID returns 404 |

## Profile, Prompt, and Billing

`UserProfile` is one-to-one with the user and stores display name and system prompt. The username is used as the display-name fallback. User ID and member-since date come from Django's user record and are read-only in the profile form.

The system prompt is read for each future generation, including later turns in an existing conversation, and is not persisted in the message transcript. The proxy client maps it to an OpenAI system message, Anthropic's top-level `system`, or Google's `systemInstruction`. It is not sent to browser configuration.

`BillingAccount` is one-to-one with a user and contains `Personal`, ACTIVE/INACTIVE status, USD currency, a decimal available balance, and timestamps. New accounts start at `$2.00 USD`. The page is display-only: there are no payment operations, ledger, or balance-based chat gate.

## CodeRange Subpath

CodeRange mounts ChitChat at `/proxy/5001/`. `DJANGO_APP_BASE_PATH` supplies that prefix to browser templates and JavaScript so navigation, forms, assets, and API calls use the mounted path. Django keeps `STATIC_URL = "/static/"`; the proxy strips `/proxy/5001` before forwarding a request to Django.

Backend redirect targets are deliberately mount-neutral: login/logout use `/accounts/login/`, login's default destination is `/`, and profile updates redirect to `/profile/`. CodeRange adds the mount prefix to root-relative `Location` headers. The login view strips the mount from an already-prefixed safe `next` value before redirecting. Keeping redirects upstream-rooted prevents a duplicated `/proxy/5001/proxy/5001/` URL.

## Persistence and Context

`Conversation` stores owner, title, provider/model selection, and timestamps. `Message` stores role, raw text/Markdown source, status, provider/model attribution for assistant turns, and a safe failure category. Message content is not rewritten for Markdown display. The ORM cascades messages when a conversation is deleted, but no delete UI/API is exposed; account deletion is not supported and protected conversation/billing relations prevent accidental removal.

New conversations are created lazily on the first prompt. The app stores that prompt and creates a pending assistant message before calling the proxy. On success, the assistant message becomes completed. On proxy failure, the prompt is retained and the assistant message is marked failed. A retry targets the latest failed assistant message and reuses its preceding user prompt.

Context construction includes only completed user/assistant pairs plus the current user prompt. Failed and incomplete turns are excluded. The entire eligible history is sent each time; token-window compaction is not implemented.

## Assistant Markdown

`static/chat/markdown.js` parses a supported Markdown subset (bold, italics, headings, unordered/ordered lists, inline/fenced code, and links). It creates only known DOM elements and inserts text with text nodes/text content. Raw model HTML is displayed as text, not interpreted. Relative links and HTTP, HTTPS, or mailto links are allowed; other explicit schemes remain plain text. User messages always use plain escaped text. Newly returned and reopened messages share `makeMessageRow`, so persisted Markdown displays consistently without changing stored content.

## Proxy Contract

The proxy's public docs document separate formats rather than one normalized endpoint:

| Interface | Endpoint | Authentication | Allowlisted model |
|---|---|---|---|
| OpenAI Chat Completions | `POST /openai/v1/chat/completions` | `Authorization: Bearer` using `BUILD_OPENAI_KEY` | `gpt-5.6-luna` |
| Anthropic Messages | `POST /anthropic/v1/messages` | `x-api-key` using `BUILD_ANTHROPIC_KEY`, plus `anthropic-version: 2023-06-01` | `claude-haiku-4-5-20251001` |
| Google Gemini Generate Content | `POST /google/v1beta/models/gemini-3.8-flash:generateContent` | `x-goog-api-key` using `BUILD_GOOGLE_KEY` | `gemini-3.8-flash` |

The app maps the same internal ordered turns to each documented request shape and parses each response separately. The model choices are a static allowlist. The proxy docs state that all three interfaces currently use DeepSeek Flash, so these are interface/model identifiers rather than distinct upstream model implementations.

Requests are non-streaming with a 90-second timeout and a 2,000,000-byte response limit. There is no automatic retry after an upstream failure. Proxy errors are mapped to safe app errors; raw upstream bodies, headers, and keys are not returned to the browser.

Source: <https://proxy.litechat.ai/docs>, <https://proxy.litechat.ai/docs/openai/chat-completions>, <https://proxy.litechat.ai/docs/anthropic/messages>, <https://proxy.litechat.ai/docs/google/gemini>.

## Code Areas

- `config/settings.py`, `config/urls.py`, `config/context_processors.py`: runtime settings, routes, and browser mount prefix.
- `chat/models.py`, `chat/migrations/`: user profile, billing account, conversation owner, and message data.
- `chat/forms.py`, `chat/views.py`, `chat/urls.py`: authentication, account pages, and private JSON APIs.
- `chat/services/accounts.py`, `chat/services/conversations.py`, `chat/services/proxy_client.py`: provisioning, owner-scoped chat lifecycle, and proxy protocol mapping.
- `chat/management/commands/`: explicit bootstrap provisioning and legacy owner assignment.
- `templates/`, `static/chat/`: responsive ChitChat interface and safe assistant Markdown rendering.

# ChitChat

ChitChat is a Django chat application with username/password accounts, per-user conversations, a profile, and a display-only personal billing account. It stores conversations and messages in SQLite and uses the server-side LiteChat proxy for a fixed set of provider-compatible models.

## Current Features

- Sign up, sign in, and sign out with Django's built-in user model, password hashing, sessions, and CSRF protection. Signup is controlled by `DJANGO_SIGNUPS_ENABLED` and is gated until a provisioned superuser exists and all conversations have owners.
- Create, continue, reopen, and retry owned conversations. History, detail, continuation, and retry lookups are scoped to the signed-in user; foreign and unknown conversation IDs return 404.
- Select among the documented OpenAI-, Anthropic-, and Google Gemini-compatible proxy interfaces when their server-side keys are configured.
- Save a per-user display name and system prompt. The prompt is passed separately to future generation requests with provider-specific mapping and is not written into the message transcript.
- Render assistant Markdown for bold, italics, headings, lists, inline/fenced code, and links. User messages remain plain text; generated markup is built with DOM APIs, raw HTML is not interpreted, and links allow safe relative URLs or HTTP, HTTPS, and mailto schemes.
- View a personal `Personal` billing account with ACTIVE status, USD currency, and a simulated `$2.00` starting balance. Billing is read-only and does not gate chat.
- Use the responsive ChitChat sidebar, account navigation, recent history, model controls, and bottom composer.
- Receive safe errors for missing provider configuration, rate limiting, timeouts, invalid/incomplete responses, and proxy failures. Failed prompts remain stored and the latest failed response can be retried.

## Important Limitations

- The CodeRange route must remain private; application signup is not a substitute for deployment access control. Public signup is disabled by default.
- There is no email verification, password reset, social login, or account deletion flow. Conversation and billing records protect user deletion.
- The proxy documentation states that all three provider-compatible interfaces currently use DeepSeek Flash. Provider labels describe API interfaces, not distinct underlying provider models.
- The model catalog is a fixed server-side allowlist. The proxy documentation does not provide a model-list endpoint.
- Responses are non-streaming and messages are text-only. Attachments, web search, tools, agents, model racing, automatic context compaction, conversation rename/delete, and import/export are not implemented.
- Context includes completed turns and the current prompt. Long histories are not automatically truncated or summarized; shorten a conversation if the proxy rejects an oversized context.
- The CodeRange target is port `5001` at `/proxy/5001/`. Subpath settings and mounted-path tests are implemented; external browser delivery and CodeRange private-access/persistence policy still depend on platform configuration. See the [CodeRange and proxy footgun](footguns/coderange-and-proxy.md).

For local and CodeRange setup, see [Setup](setup.md). For request, ownership, and persistence boundaries, see [Architecture](architecture.md).

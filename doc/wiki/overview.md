# LiteChat MVP

LiteChat is a private, single-user Django chat application. It provides a browser workspace for text conversations with a small, server-configured set of provider-compatible models. Conversations and messages are stored in SQLite and can be reopened and continued.

## Current Features

- Start a conversation by selecting an enabled provider/model and sending the first prompt.
- Continue saved conversations using completed messages reconstructed from SQLite as context.
- Reopen recent conversations from the history list.
- Select among the documented OpenAI, Anthropic, and Google Gemini proxy interfaces when the corresponding server key is configured.
- Preserve a submitted prompt when the proxy fails and retry the latest failed response without duplicating that prompt.
- Receive safe status messages for missing configuration, rate limiting, timeouts, incomplete responses, and proxy failures.

## Important Limitations

- The app has no user accounts or per-user conversation ownership. It must only be exposed behind private access control.
- The proxy documentation states that all three provider-compatible interfaces currently use DeepSeek Flash. The provider labels describe API interfaces, not distinct underlying provider models.
- The model catalog is a fixed server-side allowlist from the proxy documentation; the documentation does not provide a model-list endpoint.
- Responses are non-streaming. Streaming is documented by the proxy but is not implemented.
- Messages are text-only. Attachments, web search, tools, agents, billing, model racing, automatic context compaction, rename/delete, and import/export are not implemented.
- Context includes completed user/assistant turns plus the current prompt. Long histories are not automatically truncated or summarized; a proxy/context-size rejection must be handled by starting a shorter conversation.
- LiteChat now binds `0.0.0.0:5001`; local health, UI, static assets, provider API, and live chat flows pass. The discovered external CodeRange port-proxy URL currently refuses connections, so public-route reachability and external static serving remain unverified. See the [CodeRange and proxy footgun](footguns/coderange-and-proxy.md).

For installation and local development, see [Setup](setup.md). For request and persistence boundaries, see [Architecture](architecture.md).

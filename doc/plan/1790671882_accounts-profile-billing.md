# Multi-User Accounts, Profile, and Billing Plan

- Plan timestamp: `1790671882`
- Plan date: 2026-09-29
- Basis: `doc/study/1790671331_accounts-profile-billing.md`
- Target branch for future execution: a new feature branch from `main`
- Current repository state: working LiteChat application on `main`; auth/session middleware already installed; current local database has legacy chats without user owners.

## Goal

Add username/password accounts, authenticated chat access, per-user conversation ownership, a user profile, and a display-only personal billing account while preserving the existing LiteChat chat, provider/model selection, proxy integration, history, retry, and CodeRange subpath behavior.

Treat the current chat application as working functionality. Extend its ownership boundary and UI without rewriting the conversation/proxy implementation unnecessarily. Do not expose accounts publicly unless the CodeRange access policy is explicitly reviewed.

## Scope

- Signup with username, password, and password confirmation. Include an optional display name because the study recommends a dedicated profile field; fall back to the username when blank.
- Login, logout, authenticated sessions, and protection for the chat workspace, chat APIs, profile, and billing pages.
- Per-user chat ownership enforced in every history/detail/create/continue/retry query and service path.
- A profile page showing display name, username, the current user's ID, and member-since date; allow the user to update only their display name and their own system prompt.
- A per-user system prompt persisted on the profile and supplied to that user's subsequent proxy requests with provider-specific protocol mapping.
- One internal personal billing account per user with account name, active/inactive status, and an available credit balance. Display only; no real payments or balance purchases.
- Sidebar navigation for Chat, My Profile, Billing Account, and POST Logout while retaining New Conversation and history navigation.
- Responsive account/auth templates using the existing LiteChat design and the `/proxy/5001/` deployment mount.
- Safe handling of legacy unowned conversations; no deletion or implicit ownership assignment.
- Tests and documentation for the account, ownership, profile/system-prompt, billing, security, migration, and chat-preservation behavior.

## Out of Scope

- Google OAuth, social login, other federated sign-in, and third-party identity providers.
- Email verification, password reset email, and email-based account recovery.
- Avatar uploads, profile photos, and user-uploaded files.
- Roles beyond ordinary users; teams and shared conversations.
- Public/shared conversations.
- Admin billing dashboards, payment gateways, Stripe, PayPal, card storage, subscriptions, invoices, purchases, automatic credit replenishment, and real financial transactions.
- Usage metering, charging, credit transaction ledger, or denying chat based on balance/status unless separately approved.
- Replacing Django's current default `auth.User` with a custom user model.
- Changing the LiteChat provider catalog, proxy credentials, upstream routes, response mapping, or existing conversation UX except where required to attach ownership/system prompt.
- Changing the existing global proxy configuration into a per-user provider-key feature.

## Assumptions

- Use Django's built-in `auth.User`, `UserCreationForm`, password hashing, authentication forms/views, and database-backed sessions. Do not change `AUTH_USER_MODEL` after existing migrations have been applied.
- Signup is self-service for people who can reach the existing private CodeRange route. The route stays behind private access control; this plan does not make the application public. If public signup is intended, deployment abuse/rate controls require a separate decision.
- Use `UserProfile` as a one-to-one extension for `display_name` and `system_prompt`; derive username, account ID, and `date_joined` from the linked user.
- Create the user, profile, and billing account explicitly in one signup service/transaction. Do not use a signal as the primary provisioning mechanism. Make any repair/backfill operation idempotent with `get_or_create`.
- Give a new personal billing account the name `Personal` and active status. The initial balance is not settled; see `OPEN QUESTIONS`. Do not create non-zero credit unless explicitly approved.
- Keep billing display-only. An inactive account or zero balance does not block the existing chat flow unless a later requirement defines billing enforcement.
- Do not expose account deletion in this MVP. Use restrictive deletion behavior for conversation/billing records until retention and deletion semantics are approved.
- The user's explicit requirement that the system prompt belong to each authenticated user supersedes the earlier study's possible site-wide setting. There will be no global singleton or staff-only shared prompt in this plan.
- The CodeRange mount is `/proxy/5001/`. Authentication links, forms, redirects, assets, and JavaScript API calls must continue to resolve under that prefix; the upstream app paths remain rooted at `/` after proxy forwarding.

## OPEN QUESTIONS

1. **Legacy chat owner:** Which specific username/account should own the two existing local conversations (four messages)? If they should not be assigned, should they remain archived and inaccessible or be exported for later import? Do not run the ownership backfill or enforce a non-null owner until this is answered for the actual deployed database.
2. **Signup access:** Is self-service signup available to everyone who can reach the private CodeRange route, or should account creation be invite-only/operator-provisioned? Recommended scope is self-service username signup behind the existing private route, not public exposure.
3. **Initial billing credit and unit:** Should each new personal account start at `$0.00` or receive a simulated grant such as `$2.00`, and is the unit USD or non-cash credits? Recommended safe default is zero balance with no implicit grant; confirm denomination and display precision before migration/seeding.
4. **System prompt application:** Should a user's current saved prompt apply to new conversations only, or also to future turns in already-existing conversations? Recommended default is to load that user's current prompt on every future assistant request, including continuation, without rewriting stored messages.

Signup visibility is assumed to remain bounded by CodeRange private access; public versus invite-only deployment is not required to implement the account pages under this assumption. If this is not the intended access model, resolve it before deployment.

## Architecture

```text
CodeRange /proxy/5001/ -> Django templates and same-origin JS -> authenticated views
                          |                                  |
                          |                                  +-> owner-scoped conversation service
                          |                                  |    -> SQLite
                          |                                  +-> provider adapter with user profile prompt
                          |                                       -> existing LiteChat proxy
                          +-> auth/session middleware
```

- Keep the current `SessionMiddleware`, `AuthenticationMiddleware`, `CsrfViewMiddleware`, auth app, sessions app, password validators, and SQLite session backend. Add routes/forms/templates rather than a new authentication framework.
- Use built-in auth login/password hashing. A custom signup view based on `UserCreationForm` may add optional `display_name`, then atomically create `User`, `UserProfile`, and `BillingAccount`.
- Apply page-level login requirements to `/`, chat history/detail/write/retry APIs, `/profile/`, and `/billing/`. Keep signup, login, health, and static resources public as needed. Return redirect-to-login behavior for HTML pages and stable JSON 401 responses for API calls; update the JS client to route expired sessions to login instead of parsing a login page as JSON.
- Add a `DJANGO_APP_BASE_PATH` setting (default `/`; CodeRange `/proxy/5001/`) and expose it to templates. Use it consistently for the shared `<base>`, account links/forms, auth redirects, and `next` targets. Validate local-root and mounted-path behavior. Keep upstream `STATIC_URL` at `/static/`; do not add root-absolute account links that bypass the CodeRange prefix.
- Scope all conversation queries to `request.user`. Conversation creation assigns owner from the authenticated request only. For detail, continuation, and retry, resolve the conversation through an owner-filtered queryset before reading or changing messages. Return the same 404 for unknown and other-user IDs.
- Resolve profile and billing objects from `request.user` only; do not accept user/account identifiers from the browser.
- Keep system prompt separate from transcript messages. The conversation service obtains it from the authenticated user's `UserProfile` and passes it as an explicit argument to the existing proxy client. Map it per adapter: OpenAI system-role message, Anthropic top-level `system`, and Google's `systemInstruction`. Do not pass it through Google's existing generic non-assistant role mapping.
- Preserve current history, message lifecycle, retries, provider/model selection, and error mapping. Existing provider credentials remain server-side and globally configured as they are now.
- Preserve subpath support. Use the current relative-base approach for templates and `document.baseURI` for API paths; use prefix-aware redirects/links rather than adding unprefixed root-absolute `/accounts/...` URLs. Validate unauthenticated redirects and login `next` behavior under `/proxy/5001/`.
- On account and billing deletion, use restrictive relationships while deletion is out of scope. A later account deletion feature must define an explicit data-retention/export/purge policy.

## Files / Areas Likely to Change

- `chat/models.py`: `UserProfile`, `BillingAccount`, and nullable-then-required conversation owner relationship.
- `chat/migrations/`: profile/account tables, staged conversation-owner field/backfill, and final owner constraint migration.
- `chat/services/conversations.py`: require user/owned conversation for creation, history-related operations, continuation, and retry; apply the user's prompt without changing transcript persistence.
- `chat/views.py` and `chat/urls.py`: signup/login/logout, profile GET/update, billing display, authenticated chat APIs, owner-scoped lookups, safe JSON 401 behavior.
- `config/urls.py` and `config/settings.py`: auth routes and login/redirect settings, preserving CodeRange mount and existing session/CSRF configuration.
- `config/context_processors.py` or an equivalent shared template context helper: configured app base path for nested auth/profile/billing pages and redirects.
- `chat/forms.py` or a small account/forms module: signup form with optional display name and a profile form limited to approved fields.
- `chat/management/commands/`: explicit, idempotent legacy conversation owner backfill command that requires the chosen account identifier and refuses to guess.
- `templates/chat/index.html`, new registration/login/profile/billing templates under `templates/`, and shared account/navigation partials.
- `static/chat/chat.css` and `static/chat/chat.js`: account sidebar links, mobile behavior, auth-aware 401 handling, profile/billing page styling while preserving the current chat layout.
- `chat/tests/`: auth, ownership/IDOR, profile, billing, global prompt persistence, migration safety, and regression tests.
- `doc/wiki/overview.md`, `architecture.md`, `setup.md`, and `footguns/coderange-and-proxy.md`: update only after implementation is verified.

No new runtime dependency is expected. Do not add Django admin solely for these pages; any privileged configuration UI for future billing or global settings is out of scope.

## Database / Migration Strategy

The study observed `db.sqlite3` with two conversations, four messages, zero auth users, and no conversation owner column. That is a local ignored database and may differ from the persistent CodeRange database. The actual deployment database must be inspected read-only and backed up before changing it.

1. Confirm the legacy owner in `OPEN QUESTIONS`. Do not infer it from the first signup, default a user ID, delete the conversations, or expose ownerless conversations to all users.
2. Add `UserProfile` and `BillingAccount` with one-to-one relations to `settings.AUTH_USER_MODEL`. Create both explicitly during signup inside `transaction.atomic()`. Add a profile/account repair path using `get_or_create` for the explicitly chosen legacy user.
3. Add a nullable `Conversation.owner` FK in an initial schema migration with a swappable auth dependency. Deploy code that only lists/opens/continues owned conversations while the field is nullable; ownerless rows remain hidden from ordinary users.
4. After the named legacy account exists, run a management command such as `assign_legacy_conversation_owner --username <confirmed-name>`. Require explicit input when unowned rows exist, report counts without showing message contents, run transactionally, and be idempotent. Preserve conversation UUIDs, messages, ordering, timestamps, and provider/model attribution.
5. Verify counts and ownership on a database copy. Only after all retained conversations have an explicitly assigned owner should a later migration change the FK to non-null.
6. If human input selects archival instead of assignment, export/retain the rows with a documented access/restore policy and keep them inaccessible to all ordinary accounts; do not silently discard them.
7. Apply migrations to an actual backup/rehearsal of the CodeRange database. SQLite schema changes can rebuild/copy tables, so verify available disk space, backup restoration, row counts, migration rollback limitations, and chat behavior before production rollout.

The billing balance should have a non-negative database constraint. Seed value depends on `OPEN QUESTIONS`; recommended initial default is zero and no automatic grant. Do not include payment methods, purchase flows, or a financial ledger.

## Task Board

### A. Decisions and Preflight

- [ ] Resolve the legacy conversation owner and billing unit/initial balance questions before applying the owner backfill or billing seed.
- [ ] Confirm signup access policy (self-service behind the private route versus invitation/operator provisioning) and choose whether the optional display name appears on signup.
- [ ] Confirm the per-user system prompt applies to future turns in existing conversations or only newly created conversations.
- [ ] Record the actual deployed database path, backup procedure, conversation/message counts, auth-user count, and restoration test without reading message contents.

### B. Authentication

- [ ] Use Django's existing default `auth.User`; do not define or configure a replacement `AUTH_USER_MODEL`.
- [ ] Implement signup with username, password, password confirmation, existing validators, password hashing, CSRF, duplicate-username handling, and optional display name.
- [ ] Provision `UserProfile` and `BillingAccount` atomically with user creation; prevent duplicate related records on retries.
- [ ] Implement login and POST logout with Django auth/session APIs and same-origin CSRF protection.
- [ ] Protect the workspace and all private APIs/pages; retain deliberate public access for signup/login/health/static. Return JSON 401 from APIs and redirect HTML pages appropriately.
- [ ] Keep login, signup, logout, `next` redirects, templates, CSS, JS, and forms compatible with `/proxy/5001/`.
- [ ] Add and test `DJANGO_APP_BASE_PATH` handling for templates and authentication redirects so `/accounts/...`, `/profile/`, `/billing/`, assets, and API calls remain inside `/proxy/5001/`; retain root behavior when the setting is `/`.

### C. Models and Ownership Migration

- [ ] Add `UserProfile` one-to-one with the active auth user model; include `display_name` and a per-user `system_prompt` text field with an empty default.
- [ ] Add one-to-one `BillingAccount` with `account_name`, active/inactive status, available balance, and timestamps; add non-negative balance constraint and no payment fields.
- [ ] Add a nullable owner FK to `Conversation` first; choose restrictive user-deletion behavior until an explicit account-deletion policy exists.
- [ ] Make conversation listing, detail, continuation, and retry owner-scoped; set owner from `request.user` at creation and reject any submitted owner IDs.
- [ ] Add the explicit legacy-owner management command; abort when rows exist without a specified user; preserve all messages and conversation metadata.
- [ ] Verify legacy row counts/ownership on a database copy, then add a later migration making owner non-null only after the human mapping is complete.
- [ ] Do not mark migration tasks complete if deployed database backup, owner assignment, or row-integrity verification is unavailable.

### D. Profile, Prompt, and Billing Behavior

- [ ] Implement `/profile/` reading only `request.user`; display name, username, user ID, and `date_joined`; allow changes only to display name and that user's system prompt.
- [ ] Implement `/billing/` by resolving only `request.user.billing_account`; display personal account name, status, and available credit.
- [ ] Keep billing read-only/display-only: no purchases, cards, payment gateways, automatic credits, or chat gating based on status/balance.
- [ ] Load the profile's current system prompt for that user's future proxy requests without persisting it as a user/assistant transcript message.
- [ ] Map the prompt correctly in OpenAI, Anthropic, and Google-compatible request formats and keep it out of all other users' requests and browser-visible configuration.

### E. Navigation and Preservation

- [ ] Add Chat, My Profile, Billing Account, and a CSRF-protected POST Logout control to the existing sidebar; retain New Conversation, history, provider/model selectors, and chat controls.
- [ ] Preserve desktop/mobile layout and current visual tokens; test the account navigation at the existing mobile breakpoint.
- [ ] Update JS to handle session-expired JSON 401 responses with a prefix-safe login navigation.
- [ ] Confirm existing proxy errors, retries, message escaping, CSRF behavior, and `/proxy/5001/` asset/API paths remain intact.

### F. Documentation

- [ ] Document account creation/login/logout, session configuration, signup access policy, and protected routes.
- [ ] Document per-user conversation ownership and 404 behavior for cross-user IDs.
- [ ] Document profile fields and that user ID/member-since are read-only.
- [ ] Document the simulated billing model, chosen unit/seed, absence of real payments, and whether balance affects chat.
- [ ] Document legacy data mapping/backup/restore procedure and any ownerless archived data.
- [ ] Document per-user system prompt storage, provider-specific handling, and access restrictions if included.
- [ ] Reconcile known limitations and CodeRange subpath setup with tested implementation; never describe unverified flows as working.

## Testing

- Signup: successful creation, duplicate username, password mismatch/weak password, password hashing, optional display name, atomic profile/account creation, and idempotent related-record provisioning.
- Login/logout: valid/invalid credentials, database session, POST logout with CSRF, session flush, private page denied after logout, safe `next` redirect handling.
- Protection: anonymous access to workspace/profile/billing and all chat APIs; intended public signup/login/health/static routes; JSON 401 contract.
- Ownership: create sets current user; history scoped to current user; detail/continue/retry foreign UUID denied with same 404 as unknown IDs; forged owner fields ignored/rejected.
- Profile: own page shows display name/username/user ID/member-since; display-name and prompt update persist; a client cannot update another user's profile, username ownership, member date, or staff flags.
- Global system prompt: persists across requests/reloads, applies only to owning user's generation, does not alter stored transcript, is not exposed to another user, and maps correctly to OpenAI/Anthropic/Google request schemas.
- Billing: account created once per user, name/status/balance display, chosen zero or approved initial balance, no negative balance, no cross-user reads/updates, and no purchase or payment side effects.
- Legacy migration: empty DB path; copied legacy DB path; explicit owner assignment; missing owner argument abort; exact counts and message ordering retained; foreign users cannot see historical chats after migration.
- Existing chat regression: provider/model catalog, CSRF, prompt submission, successful response, multi-turn context, history reopen, retry without prompt duplication, safe proxy failures, text escaping, and subpath static/API URL resolution for authenticated users.

## Validation

- `python manage.py check`, complete `python manage.py test`, and `makemigrations --check --dry-run` pass.
- Migrations apply on both a fresh database and a copy of the observed legacy database without losing any conversation or message rows.
- Signup creates exactly one profile and personal billing account; account and profile records cannot be reassigned by client-supplied IDs.
- Anonymous requests cannot read/write private chat/profile/billing data; a logged-in user cannot enumerate, open, continue, or retry another user's conversation.
- The current chat provider/model selection, proxy request mapping, prompt/reply, multi-turn context, history, retry, and error behavior still work for authenticated users.
- Profile system prompt remains per-user and is mapped correctly per provider without leaking to another user or the frontend.
- Browser assets and APIs resolve below `/proxy/5001/`; auth redirects, login `next`, and logout remain usable through CodeRange.
- With `DJANGO_APP_BASE_PATH=/`, local routes and asset behavior remain compatible with existing development setup.
- Billing remains simulation-only and has no card/payment/purchase behavior; selected unit and initial balance match the approved decision.
- No credentials or password data appear in templates, JavaScript, responses, logs, or Git-tracked configuration.

## Documentation Updates

After implementation and verification, update only living docs under `doc/wiki/` and `doc/wiki/footguns/` to describe signup/login/logout, private route policy, profile and prompt behavior, per-user chat ownership, billing balance/status semantics, legacy data migration, security/session settings, tests, and actual CodeRange path behavior. Leave this study and the prior core-functionality study as historical artifacts.

## Completion Criteria

- Signup, login, logout, session protection, profile, personal billing account, and authenticated per-user chat ownership are implemented and tested.
- All chat list/detail/create/continue/retry paths filter by the authenticated owner and reject cross-user IDs.
- The user's profile system prompt persists and is applied only to that user's future provider requests with correct provider-specific mapping.
- Billing is a one-to-one internal display model only; no real payment, automatic purchase, or unapproved credit grant exists.
- The legacy conversation owner decision is explicit, migration is rehearsed from a backup, and all existing chat/message rows are preserved or deliberately archived according to the user's answer.
- Existing provider/model selection, proxy behavior, conversation context/history, responsive LiteChat UI, CSRF, and CodeRange `/proxy/5001/` compatibility continue to work.
- Tests/checks pass, documentation describes only verified behavior, and no secret is committed or exposed.

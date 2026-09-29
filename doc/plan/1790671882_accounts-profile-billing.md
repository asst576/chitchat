# Multi-User Accounts, Profile, and Billing Plan

- Plan timestamp: `1790671882`
- Plan date: 2026-09-29
- Basis: `doc/study/1790671331_accounts-profile-billing.md`
- Execution branch: `feature/accounts-profile-billing` (resumed from the same commit as `main`; not recreated).
- Repository state at plan creation: working LiteChat application on `main`; auth/session middleware already installed; current local database has legacy chats without user owners.

## Execution Progress (Resumed 2026-09-29)

- Resumed on `feature/accounts-profile-billing` from the two existing uncommitted changes in `chat/models.py` and `config/settings.py`; retained and extended that work.
- The local ignored database was initially treated as separate from deployment: 2 conversations, 6 messages, and 0 users (the message count differs from the earlier study's observation of 4). Follow-up inspection established that the active port-5001 process uses this same database; details and safe-copy verification follow.
- Rehearsed the staged migration, explicit bootstrap provisioning, owner assignment, and final owner constraint against a copy of the local legacy database. Conversation metadata and all 6 message rows/order matched the source; both chats were assigned to the rehearsal-only superuser. The source database was not migrated or modified.
- `python manage.py check`, `python manage.py test` (46 tests), and `makemigrations --check --dry-run` pass with the project virtualenv and `DJANGO_DEBUG=true`. Fresh-database migrations pass.
- Follow-up identified the active port-5001 process as using this workspace and the default `db.sqlite3` (no `DJANGO_SQLITE_PATH` override). Read-only verification found 2 conversations, 6 messages, 0 users, 0 orphan messages, and no owner column; SQLite integrity and foreign-key checks pass.
- Created a consistent SQLite online backup at `/tmp/opencode/accounts-profile-deployed-snapshot-1790674670.sqlite3` and a restore-check copy at `/tmp/opencode/accounts-profile-deployed-restore-check-1790674670.sqlite3`. Both passed integrity/FK checks and matched the source's conversation metadata and message metadata/order. No message contents were inspected, and the source database was not changed.
- Rehearsed migrations `0003` and `0004`, profile/billing provisioning, and explicit owner assignment on a separate copy of that backup using `rehearsal-only-admin`. Both legacy conversations were assigned there, zero ownerless rows remained, and all conversation/message metadata/order matched the backup. This test identity was not created or used in the active database.
- The user created the designated first/admin account `admin`; no password was requested, inspected, or recorded. After a fresh backup that included this account, the old pre-auth PID `353073` was stopped with approval, migrations `0003` and `0004` were applied, the idempotent provisioning command ran, and all 2 legacy conversations were assigned to `admin`.
- Post-migration verification confirms `owner_id` is non-null, both conversations are owned by `admin`, all 6 message rows and their metadata/order match the pre-migration backup, and the database integrity/FK checks pass. Signup was enabled only after these checks.
- The feature-branch server is running on port 5001 (PID `396507`) with `DJANGO_APP_BASE_PATH=/proxy/5001/` and `DJANGO_SIGNUPS_ENABLED=true`. Health, login, signup, anonymous API 401, and prefix-aware redirect checks passed.
- After migration, all 46 tests passed; `manage.py check`, `makemigrations --check --dry-run`, and `migrate --check` passed. A transactional smoke check against the migrated active database verified signup, login/logout, profile, billing, owned history, and cross-user 404 behavior; temporary user/session/chat changes rolled back.
- Follow-up fix: backend auth `Location` values now remain upstream-rooted (`/accounts/login/`, `/`, `/profile/`) so CodeRange adds `/proxy/5001/` once. `APP_BASE_PATH` remains on browser links/forms/assets/API paths; login `next` values already containing the mount are normalized. Regression tests cover signup/login/logout/chat redirects and account navigation with `SCRIPT_NAME=/proxy/5001`.
- After restarting the `--noreload` worker with the fix, direct upstream checks return `/accounts/login/` (not a mounted path), signup/login HTTP 200, static CSS 200, and anonymous API 401. Full suite: 48 tests pass; system/migration checks pass. The supplied public CodeRange hostname could not be fetched from this environment (transport errors), so external-browser confirmation remains unavailable.
- Added an authenticated-only sidebar greeting using the current user's non-empty profile display name or username fallback. Mounted-path tests cover missing/blank profile values and named values; all 50 tests and checks pass. The port-5001 `--noreload` worker was restarted to load the template/CSS update.
- Living-documentation tasks are intentionally deferred to the separately invoked `sync docs` phase. The user has not authorized rendezvous or merge.

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
- Custom application roles/permission hierarchies beyond Django's built-in bootstrap superuser; teams and shared conversations.
- Public/shared conversations.
- Admin billing dashboards, payment gateways, Stripe, PayPal, card storage, subscriptions, invoices, purchases, automatic credit replenishment, and real financial transactions.
- Usage metering, charging, credit transaction ledger, or denying chat based on balance/status unless separately approved.
- Replacing Django's current default `auth.User` with a custom user model.
- Changing the LiteChat provider catalog, proxy credentials, upstream routes, response mapping, or existing conversation UX except where required to attach ownership/system prompt.
- Changing the existing global proxy configuration into a per-user provider-key feature.

## Assumptions

- Use Django's built-in `auth.User`, `UserCreationForm`, password hashing, authentication forms/views, and database-backed sessions. Do not change `AUTH_USER_MODEL` after existing migrations have been applied.
- Create one operator-designated bootstrap superuser before enabling self-service signup. The bootstrap user is an explicit legacy-chat owner, not an account promoted automatically because it registered first. Keep the CodeRange route private; signup is available to users who can access that route and does not make the application public.
- Do not add email verification, email password reset, social login, or OAuth. Signup requires username/password/password confirmation and may collect an optional display name.
- Use `UserProfile` as a one-to-one extension for `display_name` and `system_prompt`; derive username, account ID, and `date_joined` from the linked user.
- Create the user, profile, and billing account explicitly in one signup service/transaction. Do not use a signal as the primary provisioning mechanism. Make any repair/backfill operation idempotent with `get_or_create`.
- Give each new personal billing account the name `Personal`, USD currency, `ACTIVE` status, and `$2.00` available credit, including the bootstrap account. This is an internal simulated starting grant only.
- Keep billing display-only. An inactive account or zero balance does not block the existing chat flow unless a later requirement defines billing enforcement.
- Do not expose account deletion in this MVP. Use restrictive deletion behavior for conversation/billing records until retention and deletion semantics are approved.
- The user's explicit requirement that the system prompt belong to each authenticated user supersedes the earlier study's possible site-wide setting. There will be no global singleton or staff-only shared prompt in this plan.
- The CodeRange mount is `/proxy/5001/`. `DJANGO_APP_BASE_PATH` will be `/` locally and `/proxy/5001/` in CodeRange; auth links, forms, redirects, assets, and JavaScript API calls must resolve under the configured prefix while upstream app paths remain rooted at `/`.

## OPEN QUESTIONS

No product decisions remain open based on the user's answers. The migration still has an execution safety gate: inspect/backup the actual deployed database and create the designated bootstrap superuser before assigning legacy conversations. These are explicit implementation tasks; they are not permission to guess an owner or discard data.

The system prompt applies to that user's future AI requests, including future turns in existing conversations, without rewriting historical messages. Billing starts at `$2.00 USD` for each newly provisioned personal account and remains display-only; no purchase or payment action is implied.

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

1. Use the designated bootstrap superuser as owner of all existing unowned conversations, as explicitly directed. Do not infer ownership from the first self-service signup, delete conversations, or expose ownerless rows to users.
2. Add `UserProfile` and `BillingAccount` with one-to-one relations to `settings.AUTH_USER_MODEL`. Create both explicitly during signup inside `transaction.atomic()`. After those tables are migrated, provision the bootstrap superuser's profile and account with an idempotent `get_or_create` service.
3. Add a nullable `Conversation.owner` FK in an initial schema migration with a swappable auth dependency. Deploy code that only lists/opens/continues owned conversations while the field is nullable; ownerless rows remain hidden from ordinary users.
4. After the bootstrap account exists, run `assign_legacy_conversation_owner --username <bootstrap-admin>`. Require that explicit username when unowned rows exist, report counts without showing message contents, run transactionally, and make the command idempotent. Preserve conversation UUIDs, messages, ordering, timestamps, and provider/model attribution.
5. Verify counts and ownership on a database copy. Confirm every retained conversation is owned by the bootstrap account and all messages remain attached in their original order.
6. Only after the backfill has been verified should a later migration change the owner FK to non-null. Ensure the application assigns an owner to every new conversation throughout the nullable transition.
7. Apply the staged migrations and command to a rehearsal copy of the actual CodeRange database. SQLite schema changes can rebuild/copy tables, so verify available disk space, backup restoration, row counts, migration rollback limitations, and chat behavior before production rollout.

The billing balance should have a non-negative database constraint and be stored as USD with two decimal places. Provision each new billing account, including the bootstrap account, with `$2.00`; this is simulated internal credit only. Do not include payment methods, purchase flows, or a financial ledger.

## Task Board

### A. Decisions and Preflight

- [x] Inspect the actual deployed SQLite database read-only; record table/row counts without inspecting message contents. Verified 2 conversations, 6 messages, 0 users, and 0 orphan messages.
- [x] Back up the deployed database and rehearse restoring the backup before any ownership migration. Verified the SQLite online backup and a separate restore-check copy at the paths recorded above.
- [x] Create the operator-designated bootstrap superuser with Django's `createsuperuser` before enabling self-service signup; never promote the first self-registered user automatically. The user-created superuser `admin` was verified without reading password data.
- [x] Use that bootstrap superuser as owner of every existing unowned conversation, as directed; record the chosen username for the backfill command. All 2 active legacy conversations are now assigned to `admin`.

### B. Authentication

- [x] Use Django's existing default `auth.User`; do not define or configure a replacement `AUTH_USER_MODEL`.
- [x] Implement signup with username, password, password confirmation, existing validators, password hashing, CSRF, duplicate-username handling, and optional display name. Do not add email verification, reset email, social login, or OAuth.
- [x] Provision `UserProfile` and `BillingAccount` atomically with user creation; prevent duplicate related records on retries.
- [x] Keep self-service signup unavailable until the bootstrap account exists and the legacy owner backfill is complete; then allow all users who can access the private CodeRange route to register. Signup is disabled by default and also checks for a provisioned superuser and zero unowned conversations.
- [x] Implement login and POST logout with Django auth/session APIs and same-origin CSRF protection.
- [x] Protect the workspace and all private APIs/pages; retain deliberate public access for signup/login/health/static. Return JSON 401 from APIs and redirect HTML pages appropriately.
- [x] Create LiteChat-styled signup/login templates with validation/error states; implement logout as a CSRF-protected POST action.
- [x] Keep login, signup, logout, `next` redirects, templates, CSS, JS, and forms compatible with `/proxy/5001/`.
- [x] Add and test `DJANGO_APP_BASE_PATH` handling for templates and authentication redirects so `/accounts/...`, `/profile/`, `/billing/`, assets, and API calls remain inside `/proxy/5001/`; retain root behavior when the setting is `/`.

### C. Models and Ownership Migration

- [x] Add `UserProfile` one-to-one with the active auth user model; include `display_name` and a per-user `system_prompt` text field with an empty default.
- [x] Add one-to-one `BillingAccount` with account name `Personal`, `USD` currency, active/inactive status, `DecimalField` available balance defaulting to `2.00`, and timestamps; add a non-negative balance constraint and no payment fields.
- [x] Add a nullable owner FK to `Conversation` first; choose restrictive user-deletion behavior until an explicit account-deletion policy exists. Migration `0003` is nullable; migration `0004` enforces non-null only after a database check.
- [x] Provision the bootstrap superuser's profile and `Personal` ACTIVE USD `$2.00` billing account using an explicit idempotent setup step. `provision_bootstrap_account --username admin` ran successfully against the active database.
- [x] Make conversation listing, detail, continuation, and retry owner-scoped; set owner from `request.user` at creation and reject any submitted owner IDs.
- [x] Add the explicit legacy-owner management command; require the bootstrap username when unowned rows exist, assign every existing conversation to that account, and preserve all messages and conversation metadata.
- [x] Verify legacy row counts/ownership on a copy of the deployed database, then add/apply the later migration making owner non-null only after the human mapping is complete. The copied deployed database passed rehearsal; after the user-selected `admin` mapping was applied and verified, migration `0004` made ownership non-null.
- [x] Do not mark migration tasks complete if deployed database backup, owner assignment, or row-integrity verification is unavailable.

### D. Profile, Prompt, and Billing Behavior

- [x] Implement `/profile/` reading only `request.user`; display name, username, user ID, and `date_joined`; allow changes only to display name and that user's system prompt.
- [x] Implement `/billing/` by resolving only `request.user.billing_account`; display `[Personal] <display name>`, status, and USD available credit.
- [x] Keep billing read-only/display-only: no purchases, cards, payment gateways, subscriptions, invoices, automatic credits, or chat gating based on status/balance.
- [x] Load the profile's current system prompt for that user's future proxy requests, including future turns in existing chats, without persisting it as a user/assistant transcript message or rewriting history.
- [x] Map the prompt correctly in OpenAI, Anthropic, and Google-compatible request formats and keep it out of all other users' requests and browser-visible configuration.

### E. Navigation and Preservation

- [x] Add Chat, My Profile, Billing Account, and a CSRF-protected POST Logout control to the existing sidebar; retain New Conversation, history, provider/model selectors, and chat controls.
- [x] Preserve desktop/mobile layout and current visual tokens; test the account navigation at the existing mobile breakpoint.
- [x] Update JS to handle session-expired JSON 401 responses with a prefix-safe login navigation.
- [x] Confirm existing proxy errors, retries, message escaping, CSRF behavior, and `/proxy/5001/` asset/API paths remain intact. The branch now runs on port 5001; mounted-path behavior is covered by tests, while external-browser delivery could not be fetched from this environment.
- [x] Keep upstream auth redirect targets mount-neutral so CodeRange injects the proxy prefix exactly once; preserve the prefix in browser-generated URLs. Regression tests reproduce `SCRIPT_NAME=/proxy/5001` and assert no duplicated path.
- [x] Display an authenticated-user sidebar greeting, preferring a non-empty profile display name and otherwise the username, without altering the existing chat/account navigation or mount behavior.

### F. Documentation

- [ ] Document account creation/login/logout, session configuration, signup access policy, and protected routes.
- [ ] Document per-user conversation ownership and 404 behavior for cross-user IDs.
- [ ] Document profile fields and that user ID/member-since are read-only.
- [ ] Document the simulated billing model, chosen unit/seed, absence of real payments, and whether balance affects chat.
- [ ] Document legacy data mapping to the bootstrap superuser and the backup/restore procedure.
- [ ] Document per-user system prompt storage, provider-specific handling, and access restrictions if included.
- [ ] Reconcile known limitations and CodeRange subpath setup with tested implementation; never describe unverified flows as working.

## Testing

- Signup: successful creation, duplicate username, password mismatch/weak password, password hashing, optional display name, atomic profile/account creation, bootstrap superuser setup, and idempotent related-record provisioning.
- Login/logout: valid/invalid credentials, database session, POST logout with CSRF, session flush, private page denied after logout, safe `next` redirect handling.
- Protection: anonymous access to workspace/profile/billing and all chat APIs; intended public signup/login/health/static routes; JSON 401 contract.
- Ownership: create sets current user; history scoped to current user; detail/continue/retry foreign UUID denied with same 404 as unknown IDs; forged owner fields ignored/rejected.
- Profile: own page shows display name/username/user ID/member-since; display-name and prompt update persist; a client cannot update another user's profile, username ownership, member date, or staff flags.
- Global system prompt: persists across requests/reloads, applies only to owning user's generation, does not alter stored transcript, is not exposed to another user, and maps correctly to OpenAI/Anthropic/Google request schemas.
- Billing: account created once per user, `Personal`/`ACTIVE`/`USD`/`$2.00` display, no negative balance, no cross-user reads/updates, and no purchase or payment side effects.
- Legacy migration: empty DB path; copied legacy DB path; every existing conversation assigned to the bootstrap superuser; missing owner argument aborts; exact counts and message ordering retained; foreign users cannot see historical chats after migration.
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
- Billing remains simulation-only with USD `$2.00` starting balance and ACTIVE status; there is no card/payment/purchase behavior or balance-based chat gate.
- No credentials or password data appear in templates, JavaScript, responses, logs, or Git-tracked configuration.

## Documentation Updates

After implementation and verification, update only living docs under `doc/wiki/` and `doc/wiki/footguns/` to describe signup/login/logout, private route policy, profile and prompt behavior, per-user chat ownership, billing balance/status semantics, legacy data migration, security/session settings, tests, and actual CodeRange path behavior. Leave this study and the prior core-functionality study as historical artifacts.

## Completion Criteria

- Signup, login, logout, session protection, profile, personal billing account, and authenticated per-user chat ownership are implemented and tested.
- All chat list/detail/create/continue/retry paths filter by the authenticated owner and reject cross-user IDs.
- The user's profile system prompt persists and is applied only to that user's future provider requests with correct provider-specific mapping.
- Billing is a one-to-one internal display model only; no real payment, automatic purchase, or unapproved credit grant exists.
- All existing conversations are assigned to the bootstrap superuser as directed; migration is rehearsed from a backup and preserves every chat/message row and its ordering.
- Existing provider/model selection, proxy behavior, conversation context/history, responsive LiteChat UI, CSRF, and CodeRange `/proxy/5001/` compatibility continue to work.
- Tests/checks pass, documentation describes only verified behavior, and no secret is committed or exposed.

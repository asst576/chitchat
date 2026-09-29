# Accounts, Profile, Ownership, and Billing Feasibility Study

- Study timestamp: `1790671331`
- Study date: 2026-09-29
- Repository branch at study: `main`
- Repository state before changes: clean worktree; `main` was 13 commits ahead of `origin/main`
- Scope: feasibility and recommended design only; no application implementation

## Executive Summary

The requested features are feasible within the existing Django 5.2, SQLite, template, and vanilla JavaScript application. The project already has Django's authentication, session, and CSRF applications and middleware installed, as well as password validators. It does not yet have login/signup routes, authenticated page protection, user-owned conversations, profile or billing models, or account navigation. All current conversation views and service lookups operate globally.

The lowest-risk design is to retain Django's existing default `auth.User` model rather than change `AUTH_USER_MODEL` after migrations have already been applied. Add a small one-to-one profile record for `display_name`, relate every conversation to `settings.AUTH_USER_MODEL`, and add a one-to-one billing account with explicitly defined credit semantics. Restrict every chat, profile, and billing query to `request.user`; UUID conversation identifiers are not an authorization mechanism.

The local ignored `db.sqlite3` is not empty: a read-only count found two conversations and four messages, while the auth-user and session tables currently contain zero rows. There is no existing owner identity to infer. Before enforcing a required conversation owner, a human must select which account, if any, should own those legacy conversations. Do not assign them to the first account that happens to sign up, delete them, or make them visible to every new user by default.

The profile and internal billing pages can be added without changing chat behavior. One scope issue needs resolution: the requested test list includes "global system prompt persistence," but no system prompt exists in the current application and it is not otherwise listed as a requested user-facing feature. If it is required, it should be designed as a site-wide setting with privileged editing and provider-specific request mapping, not as an ordinary profile field.

## OPEN QUESTIONS

1. Should signup be open to anyone with the CodeRange URL, invite-only, or restricted to a private deployment? Is email required or verified?
2. Which named account should own the existing two conversations? If they should not belong to a new account, should they be archived/exported or retained as inaccessible legacy records?
3. Should `display_name` be a separate profile field, or derived from Django's `first_name`/`last_name`? Is the default integer user ID intended only for the user's own page or as a shareable identifier?
4. Is billing balance a monetary amount or a unit of internal credits? What precision, currency/unit, initial balance, and balance grant policy are intended?
5. Does an inactive billing account or zero balance prevent chat use, or is billing display-only until metered usage and charging rules exist?
6. Who may edit the global system prompt, if it is in scope? Does changing it affect existing conversations on their next turn, or should conversations snapshot a prompt version?
7. What should account deletion do to conversations, billing records, and audit history? Account deletion is not otherwise requested.

Recommendations below identify safe defaults, but these questions should be resolved or explicitly carried into the implementation plan before irreversible migration or billing behavior is implemented.

## Reference Materials and Method

The study used the current repository code, tests, migrations, living documentation, the local SQLite database's schema and row counts (opened read-only), the user's feature list, and Django 5.2 documentation. No screenshot or other image/PDF reference assets were found in the repository; the supplied textual behavior and current LiteChat interface are the available product guidance.

The earlier MVP study/plan selected private, single-user operation and treated accounts and billing as out of scope. This new explicit request changes that product scope. The current chat UI is a Django template with a desktop vertical sidebar and a compact mobile grid; its existing new-conversation action and history behavior should remain intact.

## Confirmed Current State

- `requirements.txt` pins the Django 5.2 series and uses SQLite. No separate auth, billing, or frontend dependency is present.
- `INSTALLED_APPS` already includes `django.contrib.auth`, `django.contrib.contenttypes`, and `django.contrib.sessions`. Middleware already includes `SessionMiddleware`, `CsrfViewMiddleware`, and `AuthenticationMiddleware`.
- `AUTH_PASSWORD_VALIDATORS` is configured. `AUTH_USER_MODEL` is not overridden, so Django's default user model is in use.
- The auth context processor is installed, but `config/urls.py` has no authentication URLs and no `django.contrib.admin` app/site is installed.
- The workspace and JSON endpoints are not protected by login requirements. `conversation_list()` uses `Conversation.objects.all()`, detail lookup uses a bare primary-key lookup, and service creation/continuation/retry does not take a user argument.
- Conversations use UUID primary keys. `Message` belongs to `Conversation` with `CASCADE`; there is no owner field on `Conversation`.
- Global CSRF middleware is enabled and the existing chat POST test verifies a CSRF token is required. The interface sends the token in `X-CSRFToken`.
- No profile, billing account, global system prompt, or account navigation behavior was found in application code. The current provider request builder receives only provider/model/message context.
- The database uses `DJANGO_SQLITE_PATH` when configured and otherwise `<project-root>/db.sqlite3`; database files are ignored by Git.
- Read-only inspection of the local database found two conversation rows and four message rows, zero `auth_user` rows, and zero `django_session` rows. No conversation or message content was read. This local file may not be the deployed CodeRange database; the target deployment database must be counted and backed up separately before migration.
- Existing tests cover chat rendering, provider selection, message submit, history reopen, multi-turn context, retry, CSRF, validation, proxy errors, and model constraints. They do not cover accounts, user ownership, profiles, billing, or a global prompt.

## Feasibility and Recommended Architecture

### Django Accounts and Sessions

Django 5.2's authentication system provides password hashing, user creation helpers/forms, authentication forms/views, login/logout functions, session integration, and `login_required` protections. The existing project has the necessary middleware and session/auth apps, so account support does not require a new authentication framework.

Use Django's built-in `User` and `UserCreationForm` for this first account rollout. The form should validate the password using the configured password validators and save through Django's password-hashing APIs. Use Django's `LoginView`/`AuthenticationForm` or a thin custom view that preserves those protections. Add a custom signup view based on `UserCreationForm`; Django does not provide a complete product-specific signup page by merely enabling the auth URLs. Logout should be a CSRF-protected POST form, not a state-changing GET link.

Do not replace `AUTH_USER_MODEL` with a custom model for this feature. Although the current database has no user rows, auth migrations and the rest of the project migrations have already been applied. Django documents changing the user model mid-project as a complex schema/data migration affecting foreign keys and migration dependencies. The existing `User` supplies username, primary key, first/last name, and `date_joined`; a related model can hold LiteChat-specific profile fields.

Use explicit `login_required` decorators/mixins for the workspace, profile, billing page, and all conversation endpoints, or adopt `LoginRequiredMiddleware` only with a complete allowlist for signup, login, logout handling, health checks, and static delivery. Explicit per-view protection is easier to audit in this small application. HTML pages should redirect anonymous users to login with a safe `next` value; JSON endpoints should return a stable 401 JSON error rather than a login-page redirect that the current JavaScript client would try to parse as JSON.

The existing server-side database session backend is already configured through Django's installed sessions app/middleware. Production still needs a stable secret key, HTTPS, secure session/CSRF cookie settings, correct host/origin configuration, and a policy for session expiry and cleanup. `AuthenticationMiddleware` populates `request.user`; it does not itself require login.

If signup is public, add abuse controls and define email verification/password recovery. Django's default password backend does not provide login rate limiting. Public registration changes the exposure from the current private single-user service and should not be enabled without agreeing the audience and CodeRange access policy.

### Proposed Models

| Model | Recommended fields/relationship | Notes |
|---|---|---|
| Django `User` | Keep default user model | `username`, primary key, password hash, `date_joined`, `first_name`, and `last_name` are available. Do not store raw passwords. |
| `UserProfile` | `user = OneToOneField(settings.AUTH_USER_MODEL, ...)`; `display_name`; optional `updated_at` | The profile page obtains username, user ID, and member-since date from `request.user`; do not duplicate them as writable profile fields. A one-to-one profile is safer than a late custom auth model. |
| `Conversation` | Add `owner = ForeignKey(settings.AUTH_USER_MODEL, ...)` with an index; eventually non-null | Set owner from the authenticated request only. Never accept owner/user IDs from form or JSON input. Select an explicit user-deletion policy before choosing `CASCADE`, `PROTECT`, or another `on_delete` action. |
| `BillingAccount` | `user = OneToOneField(settings.AUTH_USER_MODEL, ...)`, `name`, active/inactive status, non-negative available balance, created/updated timestamps | One-to-one enforces one personal account per user. Store a decimal balance if the unit is fractional/monetary, or an integer if credits are indivisible; define the unit before choosing precision. No payment method or gateway is needed. |
| `GlobalChatConfiguration` (conditional) | A single site-wide setting record with `system_prompt` and update metadata | This is not a per-user profile setting. Only a privileged operator should edit it. It should not be exposed to regular account APIs. Include only if the global-system-prompt test represents approved product scope. |

For the billing MVP, an active account with a zero balance is a reasonable proposed default, but it is not confirmed. Do not grant non-zero credit, process payment, automatically purchase credit, or block otherwise working chat based on balance until the unit, initial-credit policy, and enforcement semantics are decided. Add a database check constraint against a negative balance. A mutable balance alone is not an audit ledger; if charging/metering is added later, introduce append-only credit transactions and idempotent usage accounting rather than treating this display field as a payment ledger.

For profile display, either derive a name from Django's first/last name or store a single editable `display_name` on `UserProfile`. The separate profile field best matches the requested singular display-name behavior. A sensible display fallback is `display_name`, then Django full name, then username. The user ID and member-since date should be read-only. Confirm whether the displayed ID is simply the private account's database primary key or a public opaque identifier; never use an ID in a profile URL as proof of permission.

### Conversation Ownership and IDOR Protection

Every conversation-related operation must be scoped at the query boundary, not only checked in the UI. Creation must set `owner=request.user`. History should query `Conversation.objects.filter(owner=request.user)`. Detail, continue, and retry operations should fetch the conversation from that same owner-filtered queryset before touching messages. Return the same 404 response for nonexistent and other-user UUIDs to avoid disclosing whether another account's conversation exists. UUIDs reduce guessability but are not access control.

Pass the authenticated user explicitly into conversation service operations or pass an already owner-scoped conversation object. Apply ownership checks to every read and write path, including retry and any future export/delete endpoint. Ignore or reject a client-supplied `user_id`, `owner_id`, `billing_account_id`, or profile ID. New chats must continue using the existing provider/model validation, context assembly, proxy boundary, and persistence flow.

### Profile and Billing Pages

The profile page should load only `request.user` and its own profile record. A profile update form should whitelist `display_name` (and any explicitly approved fields), not accept `user_id`, `date_joined`, password hash, staff status, or ownership. If email editing or password changes are later allowed, use the corresponding Django forms and account verification flow.

The billing page should load `request.user.billing_account`, without an account ID in the URL. Signup should create the user, profile, and personal billing account in one database transaction; use an idempotent service for provisioning any existing designated owner. Display account name, active/inactive status, and balance. No purchase, card, gateway, or automatic replenishment behavior is in scope. Decide whether inactive status is informational or blocks chat; to preserve the working chat, the recommended MVP keeps balance/status display-only until explicit usage and charging rules are adopted.

### Navigation and UI Preservation

Keep the existing chat page, provider/model selectors, history list, new-conversation behavior, composer, responsive rules, and current chat API behavior for authenticated users. Add account navigation in the existing sidebar: Chat, My Profile, Billing Account, and a POST logout form with CSRF token. Keep New Conversation and history as existing chat affordances rather than replacing them. Mark the active account/chat destination accessibly.

The current sidebar is a vertical desktop column; on narrow screens it becomes a compact grid with horizontally scrollable conversation history. Account links must fit or collapse into a compact accessible account section on mobile without hiding the existing new-chat/history functions. No reference screenshots were present in the workspace, so visual implementation should follow the current colors, type, spacing, and responsive layout rather than invent a competing design.

## Global System Prompt: Scope and Design

No global system prompt exists in the current model, conversation service, or proxy client. The user asks for a test for "global system prompt persistence," so this appears to be an implied feature but needs confirmation because it is not included elsewhere in the feature list.

If approved, store the prompt in a single site-wide configuration record and load it server-side for each generation. Restrict edits to an operator/staff-only settings surface; ordinary users should not read or modify it through profile or billing APIs. Decide whether conversations use the current prompt each turn or snapshot a version when created. The simplest global-policy behavior is to use the current persisted prompt on every turn, but this changes behavior for already-open conversations and should be explicit.

The current proxy adapters require different wire representations: OpenAI accepts a system-role message; Anthropic uses a top-level `system` value; Google uses `systemInstruction`. In the existing Google adapter, every non-assistant role is converted to a user role, so adding a generic `role="system"` message to the existing list would be wrong. Thread a separate system-prompt argument through the service and map it per provider, with request-shape tests for all adapters. Preserve user/assistant transcript records separately from the global instruction.

## Existing Conversation Data and Migration Safety

### Observed state

The local ignored SQLite file contains two conversations and four messages, but zero user records. The current schema has no owner field. This confirms that at least this local database has legacy chat data with no owner mapping. It does not prove the deployed CodeRange database has identical counts; inspect and back up the actual deployment database separately.

### Safe options

| Option | Preserves data? | Considerations |
|---|---|---|
| Assign all legacy conversations to a specifically designated founding/owner account | Yes | Appropriate only if a human confirms that account should own every historical chat. The observed database has no account to map automatically. |
| Keep legacy conversations nullable/unowned and inaccessible to ordinary accounts | Yes | Safest temporary compatibility path, but does not satisfy the eventual invariant that every conversation has an owner. Requires a documented archive/assignment decision. |
| Export/archive the legacy rows, then start user-owned conversations in the active schema | Yes, if export/restore is verified | Separates old history from new user data, but changes where legacy chats are viewed and requires retention/access policy. |
| Delete or assign to the first account that signs up | No or unsafe | Not recommended; destructive or transfers potentially private history to an arbitrary user. |

### Recommended staged rollout

1. Back up the actual SQLite database and rehearse against a copy. Record conversation/message counts and verify a restore procedure before any production migration.
2. Add a nullable owner foreign key with an explicit `AUTH_USER_MODEL` migration dependency. During the intermediate state, all application reads must already be owner-filtered so null-owner legacy rows are invisible to normal accounts.
3. Create the explicitly chosen legacy owner account and run an idempotent, audited one-time management command that assigns legacy conversations only after receiving an explicit account identifier. If rows exist and no owner is provided, the command should stop without changing data.
4. Verify every original conversation remains, message counts/content/order remain intact, no ownerless conversations remain, and all current chat/API tests still pass on a migrated copy.
5. Only after the backfill is approved should a later migration make the owner field non-null. If the human decision is to preserve unowned history, do not run this final enforcement until an archive/legacy policy is approved.

Django data migrations should use historical models and deterministic migration dependencies. Avoid a migration that assigns to "the first user," guesses a user by email, deletes unowned conversations, or depends on an undocumented runtime environment variable. SQLite schema alterations may rebuild/copy tables; run the migration during an approved maintenance window on a backup and verify counts before exposing the upgraded application.

## Security Assessment

- **Password handling:** use Django's user-creation/authentication forms and password APIs. Passwords remain hashes; never store or log raw passwords. Existing validators already include similarity, minimum-length, common-password, and numeric-password checks.
- **Authenticated sessions:** the project already has database-backed sessions and `AuthenticationMiddleware`; use Django login/logout APIs. Configure HTTPS-only secure cookies, HttpOnly/SameSite policy, stable `SECRET_KEY`, session expiry, and expired-session cleanup to match CodeRange.
- **Login protection:** require auth for workspace and all private chat/profile/billing APIs. Keep signup/login and health checks public as deliberately chosen. Ensure JSON API unauth responses are machine-readable rather than HTML redirects.
- **CSRF:** existing `CsrfViewMiddleware` and tests are useful foundations. Keep CSRF on signup, profile updates, chat writes, billing updates if any, and POST logout. Do not make state changes through GET.
- **Conversation IDOR:** filter by current user in every queryset and service path. Test another user's UUID on list/detail/continue/retry. A 404 for both foreign and unknown IDs is preferable.
- **Profile/billing ownership:** take the user from the authenticated request, never from submitted IDs. A billing account or profile primary key in a URL must not permit access to another user's record.
- **Billing integrity:** keep balance read-only to users and never accept a client-submitted balance/status. Add non-negative DB constraints. If future charges are added, use transaction-safe, idempotent ledger entries and audit who changed credits.
- **Signup abuse:** choose open vs invite-only registration. Open signup requires abuse controls such as rate limiting and potentially email verification; Django's default password backend does not rate-limit login attempts.
- **Deployment privacy:** the current project has no built-in auth and CodeRange private-access behavior remains unverified. Keep all pages behind the new account checks and keep the CodeRange route private. Confirm HTTPS, trusted origins, secure cookies, and host validation; do not trust proxy headers without platform confirmation.
- **Global prompt:** treat the prompt as privileged configuration. Do not send it to clients or ordinary account APIs; include it only in server-side proxy requests.

## Recommended Test Strategy

| Area | Recommended tests |
|---|---|
| Signup | Valid account creation; duplicate username; password mismatch/weak password; password stored as a hash; profile and exactly one personal billing account created atomically; account cannot be duplicated on retry. |
| Login/logout | Valid and invalid credentials; session established; logout is POST/CSRF-protected and flushes the session; login redirects only to a safe local `next` URL. |
| Protected pages | Anonymous workspace, profile, billing, conversation-list/detail/write/retry requests are denied appropriately; health, login, signup, and static routes remain intentionally accessible. JSON APIs return stable 401 behavior. |
| Profile | Own profile displays username, ID, display name, and `date_joined`; only approved fields update; tampering with user IDs, username ownership, or member date cannot change another user/account. |
| Global system prompt | Save a prompt, reload from the database, and verify the persisted value is supplied on a subsequent generation; confirm only privileged actors can edit/read it; assert provider-specific OpenAI/Anthropic/Google request mapping and no client exposure. |
| Billing | Signup creates one account; repeated provisioning remains one-to-one; page displays name/status/balance; negative balance rejected; user A cannot read or edit user B's account; no purchase/payment side effect occurs. |
| Ownership/IDOR | User A sees only A's history; user B cannot detail, continue, or retry A's UUID; creation always assigns request user; forged `owner_id` is ignored/rejected; foreign and nonexistent UUIDs use the same not-found behavior. |
| Legacy migration | Empty DB migrates; a copied DB with two conversations/four messages remains intact; no owner assignment occurs without explicit mapping; chosen mapping assigns all rows and preserves message order/counts; migration refuses final non-null enforcement while orphan rows remain. |
| Preserve chat | Existing provider list, provider selection, prompt send, live/mock response, multi-turn context, reopen/history, proxy errors/retry, CSRF, and subpath static/API behavior continue to pass for authenticated users. Keep mocked-proxy tests offline and run an explicit live smoke only when authorized/configured. |

## Recommended MVP Scope and Sequence

1. Resolve signup policy, profile/display-name semantics, legacy conversation owner, billing unit/initial credit/status behavior, user deletion policy, and global system prompt scope.
2. Add signup/login/logout flows using Django's default user, protect the workspace/APIs, and add authentication/session tests. Keep the existing chat UI available only after authentication.
3. Add a one-to-one profile record and own-profile page/update flow.
4. Add nullable conversation ownership and owner-scoped query/service behavior, then explicitly backfill legacy conversations and enforce non-null ownership after validation.
5. Provision and display a personal billing account; keep billing display-only, with zero initial credit unless a separate grant policy is approved. Do not add payment processing.
6. Add sidebar navigation without replacing existing chat/history controls; review responsive behavior on mobile and desktop.
7. Decide whether the global system prompt belongs in scope; if approved, add privileged persisted configuration and provider-specific adapter/tests as a separate task.

This sequence preserves the current chat/proxy service boundary and avoids a late custom-user-model substitution or silent ownership transfer. No application code was changed during this study.

## References

- Django 5.2 authentication system: <https://docs.djangoproject.com/en/5.2/topics/auth/default/>
- Django 5.2 authentication customization, profile models, and user-model substitution guidance: <https://docs.djangoproject.com/en/5.2/topics/auth/customizing/>
- Django 5.2 sessions: <https://docs.djangoproject.com/en/5.2/topics/http/sessions/>
- Django 5.2 CSRF protection: <https://docs.djangoproject.com/en/5.2/ref/csrf/>
- Django 5.2 migrations, data migrations, and SQLite schema limitations: <https://docs.djangoproject.com/en/5.2/topics/migrations/>
- Django 5.2 model constraints: <https://docs.djangoproject.com/en/5.2/ref/models/constraints/>
- Existing product reference study: `doc/study/1790658228_litechat_core_functionality_feasibility.md`.

## Study Completion

This document is a feasibility study only. No implementation, plan, canonical documentation, existing database row, or living wiki file was modified as part of the study phase.

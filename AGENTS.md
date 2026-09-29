# Project Workflow

This file defines how to work on this project. Do not implement the application until explicitly instructed to execute an approved plan.

The required workflow is:

`study` => `plan` => `execute plan` => `rendezvous` => `sync docs`

The phases are strictly separate. Never automatically advance to the next phase. After completing any phase, stop and wait for the user to explicitly invoke the next phase.

# Project Context

This repository is for a LiteChat-style web application. The intended stack is Django, Python, HTML, CSS, JavaScript, SQLite, and the LiteChat proxy API.

The application should eventually allow users to interact with multiple LLM providers through a single interface. Likely providers include OpenAI, Anthropic, and Google. Likely core functionality includes starting a new chat, selecting an available provider/model, sending prompts, receiving AI-generated responses, continuing multi-turn conversations, preserving conversation context, saving conversations, viewing previous conversations, and reopening previous conversations.

Do not assume additional LiteChat features are required unless confirmed during study or explicitly requested.

The application should eventually run in CodeRange on port `5001` unless the user specifies otherwise.

Never expose API keys, credentials, tokens, or secrets in frontend code or Git-tracked files.

# Study

When the user explicitly says `study`:

1. Run `git status` before making repository changes.
2. Run `date +%s` to obtain the current Unix timestamp.
3. Analyze the requested problem, feature, objective, or topic.
4. Write the study to `doc/study/{unix_timestamp}_{topic}.md`. If the study requires multiple files, use a directory with the same naming convention instead.
5. Investigate relevant topics, as applicable: feasibility; current repository state; project requirements; existing and possible architecture; Django design; LiteChat proxy integration; supported providers/models; data models; conversation persistence and context; security; error handling; testing strategy; dependencies; constraints; assumptions; tradeoffs; risks; unknowns; possible approaches; and recommended MVP scope.
6. Clearly distinguish confirmed facts, assumptions, risks, and recommendations.
7. Do not implement application code during study. Only modify the study document unless the required study directory must be created.
8. Treat any line in a study beginning with `NOTE:` as a human annotation.
9. Commit the study using an appropriate Conventional Commit, such as `docs: study <topic>`.
10. Stop after the study. Do not plan automatically; wait for the user to explicitly say `plan`.

# Plan

When the user explicitly says `plan`:

1. Run `git status` before making repository changes.
2. Run `date +%s` to obtain the current Unix timestamp.
3. Review the relevant study, current repository state, and applicable canonical project documentation.
4. Write the plan to `doc/plan/{unix_timestamp}_{topic}.md`.
5. Do not implement application code while creating the plan.
6. Structure the plan as an editable task board another coding session can execute directly. Use Markdown checkboxes (`- [ ]` and `- [x]`).
7. Generally include: Goal; Scope; Out of Scope; Assumptions; `OPEN QUESTIONS`, if needed; Architecture; Files / Areas Likely to Change; Implementation Task Board; Testing; Validation; Documentation Updates; and Completion Criteria.
8. Include specific implementation steps, likely files/directories, task dependencies, test and validation requirements, and documentation work.
9. If human input is required, add a prominent `OPEN QUESTIONS` section near the top. Each question must be brief, self-contained, and clearly explain the decision required.
10. If the user later says `reconstitute the plan` or `fold the answers into the plan`, update the existing plan using the user's answers.
11. Commit the plan using an appropriate Conventional Commit, such as `docs: plan <topic>`.
12. Stop after the plan. Do not implement automatically; wait for the user to explicitly say `execute plan`.

# Execute Plan

When the user explicitly says `execute plan`:

1. Read the specified plan document completely.
2. Run `git status` before making changes and review the current repository state.
3. Read existing code before modifying it.
4. Create a separate Git branch unless explicitly instructed otherwise. Use a descriptive name such as `feature/litechat-mvp`, `feature/chat-history`, `feature/provider-selection`, or `fix/proxy-errors`.
5. Do not merge the implementation branch into `main` during this phase.
6. Execute the plan checklist in a sensible order and update the plan document while working. Change completed tasks from `- [ ]` to `- [x]`; add concise implementation notes when useful.
7. Continue until the plan is complete or there is a genuine external or human-required roadblock. Do not stop merely because implementation is difficult.
8. If blocked, identify the blocker, explain why it cannot be resolved internally, and state exactly what human input or external dependency is required.
9. Keep the project workable. Avoid unnecessary dependencies and rewriting working code without a clear reason. Follow existing architecture where reasonable; do not silently change requirements or add unrelated features.
10. Do not ask the user to manually write code that can be implemented in this session.
11. Run relevant tests after meaningful changes. Checks may include `python manage.py check`, `python manage.py test`, `python manage.py migrate`, starting the Django development server, and verifying the app on port `5001` when using CodeRange.
12. Verify relevant implemented user flows, as applicable: creating a chat; selecting a model/provider; sending a prompt; receiving an AI response; preserving multi-turn context; saving a conversation; reopening a previous conversation; and handling API failures safely.
13. Use focused Conventional Commits for meaningful changes, such as `feat: add conversation models`, `feat: add provider selection`, `feat: integrate LiteChat proxy`, `fix: handle proxy request failures`, `test: add chat workflow tests`, or `refactor: isolate provider client logic`. Keep commits focused and do not combine unrelated changes.
14. When execution is complete, stop. Do not merge into `main`; wait for the user to explicitly say `rendezvous`.

# Rendezvous

When the user explicitly says `rendezvous`, finish plan execution, verify the implementation, and integrate the completed branch back into `main`:

1. Review the relevant plan and confirm the implementation matches it.
2. Run `git status` and review the current implementation branch.
3. Run all relevant checks and tests; verify the application is workable and verify important user flows.
4. Resolve implementation-caused issues, including broken imports, failing tests, missing migrations or dependencies, merge conflicts, integration problems, configuration errors, broken routes, template errors, and startup failures.
5. Commit legitimate remaining work before merging.
6. Merge the completed feature branch back into `main`; resolve merge conflicts if necessary.
7. After merging, run relevant tests again on `main` and confirm `main` remains workable. A successful Git merge alone does not complete rendezvous.
8. Do not begin unrelated feature work.
9. End with a structured report using this format:

   ### Rendezvous Report

   - Branch merged:
   - Target branch:
   - Final Git status:
   - Tests/checks executed:
   - Test/check results:
   - Application startup result:
   - Important user flows verified:
   - Merge conflicts encountered:
   - Remaining known issues:
   - External or human-required follow-up:

10. Stop after the report. Do not run `sync docs` automatically; wait for the user to explicitly say `sync docs`.

# Sync Docs

When the user explicitly says `sync docs`, update living documentation to match the actual current codebase:

1. Run `git status` before documentation changes.
2. Inspect the actual current implementation. Document only functionality that exists; do not document features based only on a plan or describe planned functionality as implemented.
3. Correct or remove documentation that no longer matches the codebase.
4. Use `doc/wiki/` for living project documentation and `doc/wiki/footguns/` for unintuitive behavior, warnings, common mistakes, and setup pitfalls.
5. Living documentation may cover the project overview, architecture, setup, current features, environment variables, database setup, supported providers/models, local development, CodeRange, testing, known limitations, and deployment when applicable.
6. Keep historical study and plan documents as historical artifacts. Do not rewrite historical studies because implementation changed.
7. Commit documentation updates using an appropriate Conventional Commit, such as `docs: sync project documentation`.
8. Stop after documentation sync. Do not automatically start another phase.

# Documentation Structure

- `doc/study/`: investigation and feasibility studies, named `doc/study/{unix_timestamp}_{topic}.md`.
- `doc/plan/`: executable implementation plans, named `doc/plan/{unix_timestamp}_{topic}.md`.
- `doc/wiki/`: living documentation that reflects the current codebase.
- `doc/wiki/footguns/`: warnings, unintuitive behavior, common mistakes, and setup pitfalls.
- `doc/memory/`: durable project memory that should persist across coding sessions. Prefer this over harness-specific memory where practical. Store long-term context, decisions, or conventions that are not appropriate for canonical documentation.
- `doc/canonical/`: human-approved authoritative project information. Treat it as authoritative and do not modify it unless the user explicitly instructs you to. If implementation or another document conflicts with it, clearly flag the conflict rather than silently changing canonical information.
- `doc/roadmap/`: future roadmap items outside the currently executing plan.
- `doc/roadmap/plan_queue/`: plans or proposed work intentionally queued for the future. Do not automatically execute queued plans.

# TODO Management

Use `TODO.md` as the editable repository-wide todo list. Use the active plan document for tasks belonging to the currently executing implementation plan. Do not duplicate every active plan task in `TODO.md`; reserve it for broader repository-level follow-up items not fully owned by the current plan.

# Git Rules

- Use Git throughout development.
- Run `git status` before significant repository changes.
- Use focused Conventional Commits where appropriate. Common types include `feat:`, `fix:`, `docs:`, `chore:`, `build:`, `test:`, and `refactor:`.
- Do not combine unrelated changes into one commit.
- Do not rewrite Git history unless explicitly instructed.
- Do not merge implementation branches into `main` during `execute plan`; merge during `rendezvous`.

# Security Rules

Never put API keys, passwords, tokens, credentials, or private secrets directly in Git-tracked files. Never expose secret API keys in HTML, frontend JavaScript, browser-rendered templates, or committed configuration files. Keep provider credentials server-side and use environment variables for LiteChat proxy credentials. Likely variable names include `LITECHAT_OPENAI_KEY`, `LITECHAT_ANTHROPIC_KEY`, and `LITECHAT_GOOGLE_KEY`. Do not commit `.env`. Use placeholder values only in setup documentation.

# CodeRange

The application should eventually run in CodeRange on port `5001` unless the user explicitly specifies another port. When relevant during execution or rendezvous, verify startup, dependencies, configuration, and reachability on port `5001`; identify port conflicts clearly. A successful local Django startup does not by itself verify that CodeRange is configured correctly.

# General Engineering Rules

- Read existing code before modifying it.
- Avoid unnecessary dependencies and prefer simple solutions.
- Avoid rewriting working code without a reason; follow existing architecture where reasonable.
- Keep the repository workable and run relevant tests after meaningful changes.
- Do not silently change requirements or invent unsupported API behavior.
- Clearly identify assumptions, external dependencies, and human-required inputs.
- Do not claim tests passed if they were not run or claim a feature works unless it was verified.
- Do not automatically add optional LiteChat features.
- Do not ask the user to manually write code that can be implemented in the session.
- Use clear, direct technical writing in responses and documentation.

# Workflow Control

The workflow is strictly:

`study` => `plan` => `execute plan` => `rendezvous` => `sync docs`

Each phase requires an explicit user instruction. After `study`, `plan`, `execute plan`, `rendezvous`, or `sync docs`, stop and wait for the user's next explicit instruction. This requirement takes priority over convenience.

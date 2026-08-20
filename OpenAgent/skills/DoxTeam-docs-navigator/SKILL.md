---
name: DoxTeam-docs-navigator
description: Navigate and explain local DoxTeam documentation while routing module and API questions to the right sources and warning against Hikka assumptions.
keywords:
  - docs
  - documentation
  - doc
  - API_DOC.md
  - doxteam
  - api
  - module
  - modules
  - hikka
  - cпpaвкa
  - дoкyмeнтaция
---

# DoxTeam Docs Navigator

Use this skill when the user asks to find, read, explain, or cross-reference local DoxTeam documentation, API guides, module docs, inline docs, or examples.

## Main goal

Answer DoxTeam documentation questions from local project sources first, with precise file paths and clear routing to the correct DoxTeam workflow when the question becomes implementation, debugging, or release work.

## Primary sources

Start with these local documents when present:

- `API_DOC.md` for the documentation index and API overview.
- `doc/registration/class-style.md` for class-style modules.
- `doc/guides/module-structure.md` and `doc/guides/best-practices.md` for module layout and conventions.
- `doc/inline/inline-form.md` and `doc/inline/callbacks.md` for inline forms and callbacks.
- `doc/api/module-config.md`, `doc/api/database.md`, and `doc/api/errors.md` for config, persistence, and error handling.
- Existing modules under `app-debug/` or release module folders only as examples, not as documentation authority.

## Workflow

1. Identify the documentation topic and likely source file.
2. Read the closest local docs before answering.
3. Quote or summarize only the relevant section; avoid dumping long files.
4. Include exact paths so the user can inspect the source.
5. If docs conflict with code, say so and recommend verifying against current implementation.
6. Route follow-up implementation to `DoxTeam-modules-creator`, debugger fixes to `DoxTeam-debugger-fixer`, audits to `DoxTeam-module-auditor`, and releases to `DoxTeam-release-modules`.

## DoxTeam-specific rules

- DoxTeam modules are not Hikka modules.
- Do not answer DoxTeam API questions using Hikka imports, base classes, or registration patterns.
- Treat DoxTeam as a Telethon-based userbot unless docs explicitly discuss the auxiliary bot layer.
- Prefer documented DoxTeam helpers such as `ModuleBase`, `@loader.command`, `self.edit`, `self.answer`, `self.db`, `self.cache`, and inline callback APIs when the docs support them.

## Response style

Keep answers practical:

- `Source`: path(s) used.
- `Answer`: concise explanation.
- `Use this when coding`: short actionable notes.
- `Next workflow`: name the skill to use if the user wants code changes.

## Safety rules

- Do not invent undocumented DoxTeam APIs.
- Do not expose secrets from examples or runtime config.
- Do not edit files in this docs-only workflow unless the user explicitly asks to update documentation.

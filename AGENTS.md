# Project Instructions

Before taking any task action, read `CLAUDE.md` in full.

Treat `CLAUDE.md` as the primary project instruction file. Follow its
instructions unless they conflict with Codex's system, safety, or sandbox
requirements.

Unless a passage is explicitly about Claude-only configuration or UI,
references to "Claude" or "Claude Code" also apply to Codex.

Before writing, editing, or reviewing Stata, R, or Python code, read
`.claude/skills/coding/SKILL.md` in full.

When the user requests a code audit or `/code-audit`, read and follow
`.claude/commands/code-audit.md`. When the user requests a paper review or
`/review-paper`, read and follow `.claude/commands/review-paper.md`.

Inspect other contents of `.claude/skills/` and `.claude/commands/` when they
are relevant to the current task, and read the relevant source before
proceeding.

When a task depends on machine-specific storage paths, read
`CLAUDE.local.md`. Treat its contents as private, machine-local configuration;
do not quote or commit populated paths unless explicitly requested.

`.claude/settings.json` is Claude-specific. Do not assume its permissions or
hooks apply to Codex.

Do not duplicate or rewrite the instructions from `CLAUDE.md` into this file.

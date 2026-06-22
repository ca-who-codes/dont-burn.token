---
name: write
description: Documentation, commit messages, emails, specs, and PRDs. Load this for any task that produces prose or structured documents.
allowed-tools: Read, Write, Edit, WebSearch
---

# Write Skill

## Before writing

Read only what defines the style and scope:
- `CLAUDE.md` / `AGENTS.md` — project tone (already loaded)
- One existing example of the document type — not all of them
- The specific section being changed — not the whole doc

## Commit messages

```
<type>(<scope>): <what changed and why in ≤72 chars>

- bullet for non-obvious detail
- another if needed
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`

Never start with "Update", "Change", "Modify" — those describe what git diff already shows.

## Documentation

- Lead with what the thing does, not what it is
- One sentence per concept
- Code example before prose explanation, not after
- Skip: "This document describes...", "In this section, we will..."

## Emails / outreach

- Subject: specific, ≤60 chars, no "Following up on..."
- Body: context (1 sentence) → ask (1 sentence) → why it matters to them (1 sentence)
- No sign-off paragraph

## PRDs / specs

Structure:
```
## Problem
<one paragraph, measured impact>

## Solution
<what it does, not how it works>

## Success metrics
- <metric>: <target>

## Out of scope
- <explicit exclusion>
```

No "Background", no "Executive Summary", no history lesson.

## Output rules

- Write the document directly — no "Here is the X:"
- Do not summarize what you wrote after writing it
- Revisions: show the changed section only, not the whole doc

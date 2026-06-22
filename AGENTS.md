# dontburn — Agent Rules

These rules apply to all AI agents (Claude, Codex, Gemini, etc.) working in this repo. For Claude Code specifically, CLAUDE.md takes precedence on conflicts.

---

## Startup sequence

```
read CLAUDE.md                     → behavior rules
read snapshot/project.md           → codebase map (if present)
read skills/index.md               → available skills
read session/corrections.md        → past session learnings
match task → skill → load skill file
```

Do not skip any step. The startup read costs ~500 tokens and saves 5,000–50,000.

---

## Context budget

Each session has an implicit budget. Spend it like this:

| Phase | Budget share | What to load |
|-------|-------------|--------------|
| Orientation | 5% | Snapshot + skills index + corrections |
| Task execution | 85% | Only files directly needed for the current task |
| Output | 10% | Diffs, summaries, results |

Never spend orientation budget on files that will not be touched this session.

---

## Multi-agent handoffs

When passing context to another agent:
1. Include only the task, the relevant snapshot section, and the skill to use
2. Do not pass the full conversation history — compress it to: goal + decisions made + open questions
3. Use `session/corrections.md` as shared state between agents in the same session

---

## Tool use

- One tool call per goal. If two goals are independent, call both tools in one message.
- Never call a tool to confirm information already in context.
- If a tool output is >2000 tokens, extract only the relevant fields before reasoning.

---

## Corrections

After a session, if you discovered a behavioral pattern to avoid or repeat:
1. Append it to `session/corrections.md` in the format: `- [date] rule: <rule>. reason: <why>`
2. Do not modify CLAUDE.md directly — corrections accumulate in the corrections file
3. Run `python session/learn.py` to distill corrections into CLAUDE.md entries

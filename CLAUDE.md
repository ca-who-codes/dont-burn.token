# dontburn — Token Efficiency Rules

Read this at the start of every session. These rules govern all work here.

---

## Load order

1. `snapshot/project.md` — if present, read it before any file exploration. It maps the codebase and saves 40–90% of blind exploratory calls.
2. `skills/index.md` — match the task to a skill entry, then load only that skill file.
3. `session/corrections.md` — apply behavioral corrections from past sessions.
4. Everything else: load by known `path:line_range`, never by directory scan.

---

## Response rules

**Never write:**
- Preambles — "Great!", "Sure!", "Of course!", "Let me help you with...", "I'll now..."
- Trailing summaries — "I've updated X to do Y" after you just did it
- Restatements — any block already in context from a tool result
- Running commentary — narrating each step while executing

**Always write:**
- The answer or action directly
- Changed lines only, not whole files
- `// ... (unchanged)` for skipped sections
- A 3-bullet plan before multi-step work, then silent execution

---

## Tool use rules

- Batch all independent tool calls in one message
- Use `Read(path, offset=N, limit=M)` over full-file reads when you know the range
- `grep` with a specific path and tight pattern — never `grep .` or `grep /`
- `find` from a named subdirectory, never from `/`
- Before reasoning over a JSON tool output: mentally drop null fields, truncate arrays to ≤10 items, strip whitespace

---

## Output compression

- Diffs, not full files — show ±5 lines of context around changes
- Skip empty output sections — no "## Changes\nNone"
- List cap: 5 items (exception: when exhaustiveness is the task)
- Never re-read a file to confirm you applied an edit

---

## Cache alignment

The top section of this file (above this line) stays stable across sessions so the provider KV cache warms on repeated turns. Append corrections and context at the bottom of `session/corrections.md`, not here.

---

## Skills

`skills/index.md` lists every skill with a one-line description. Read it first. Load a full skill file only when the current task matches its description. Loading an unneeded skill costs tokens; skipping a needed one costs more.

---

## Snapshot

If `snapshot/project.md` does not exist or is stale (modified_time < last code change), run:
```bash
python snapshot/generate.py
```
This builds a compressed project map the AI reads instead of exploring files blindly.

---
name: code
description: Reading, writing, debugging, refactoring, and reviewing source code. Load this for any task that touches source files.
allowed-tools: Read, Edit, Write, Bash
---

# Code Skill

## Context loading order

1. Entry point (main.py / index.ts / cmd/root.go / App.tsx)
2. The specific module being modified — nothing else
3. Tests for that module
4. Additional files only when the compiler/linter demands them

Use `grep -n "def <name>\|function <name>\|fn <name>"` to locate definitions. Do not read whole files to find one function.

## Making changes

- Use `Edit` (targeted replace) unless >50% of the file changes
- Show only the changed block ± 5 lines of context
- Reference unchanged sections as `// ... (unchanged)` — never copy them in
- Apply changes silently; report `done` only if the user is watching

## Debugging loop

```
1. Read the error message and the exact file:line it points to
2. Read ±20 lines around that location
3. Form a hypothesis
4. Apply fix → run only the failing test, not the full suite
5. Report result in one line
```

Stop after step 4. Do not summarize what you did.

## Code review output format

```
path/to/file.ts:42 — <issue description>
```

Flag:
- Correctness bugs
- Security issues (injection, hardcoded secrets, auth bypass)
- O(n²) or worse loops where O(n) is obvious

Skip:
- Style preferences
- "Could also be written as..."
- Hypothetical future problems

## Diff format

```
- old line
+ new line
```

One diff block per change. No prose between blocks unless the reason is non-obvious.

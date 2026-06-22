# Output Shaper

Rules for reducing tokens the model writes back. Output costs 5× input on premium models — this is where the big savings are.

---

## Verbosity steering (append to system prompt tail)

Add this text to the **end** of any system prompt. Placing it at the end keeps the beginning stable for KV-cache hits.

```
---
RESPONSE STYLE: terse. No preambles, no trailing summaries, no restated context. Answer directly; stop when done. Diffs over prose; changed lines only.
```

## Effort routing

Not every turn needs deep reasoning. Apply reduced effort when:
- The turn is a pure tool-result acknowledgment (file read, passing test)
- The task is mechanical (rename, format, move)
- The question is factual with an obvious answer

Apply full effort when:
- The user asks a new design or architecture question
- A test fails unexpectedly
- There is ambiguity in the task

## Response size targets

| Task type | Target tokens | Cap |
|-----------|--------------|-----|
| Single file edit | 50–200 | 400 |
| Bug fix with explanation | 100–300 | 600 |
| Code review | 200–500 | 800 |
| Architecture explanation | 300–700 | 1200 |
| Full document draft | 500–2000 | — |

If you find yourself exceeding the cap, ask: "Can I show a diff instead of the full file?"

## Anti-patterns to eliminate

| Pattern | Instead |
|---------|---------|
| "I've updated X to Y" | (nothing — the edit speaks) |
| "Here is the updated file:" | (just show the file) |
| "Let me know if this works" | (nothing) |
| "To summarize what I did:" | (nothing) |
| Reprinting code you just read | `// ... (unchanged)` |
| "The error is on line N, which says..." | `file.ts:N — description` |
| "Great question!" | (nothing) |

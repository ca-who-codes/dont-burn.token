# Cache Alignment

How to structure prompts so provider KV caches actually hit. Misaligned caches waste 40–90% of input cost on repeated turns.

---

## How KV caching works

The provider caches the computed attention for the prefix of each prompt. On the next turn, if the prefix is identical, it reuses the cache instead of recomputing.

**Cache hit**: prefix matches → pay only for new tokens  
**Cache miss**: prefix differs by even one token → pay for everything

---

## Rules

### 1. Keep the system prompt stable

Never vary the system prompt between turns in a session. If you need to update it, update it once at the start — not mid-session.

Bad:
```
Turn 1 system: "You are a helpful assistant. Today is Monday."
Turn 2 system: "You are a helpful assistant. Today is Tuesday."
```

Good:
```
Turn 1 system: "You are a helpful assistant."
Turn 2 system: "You are a helpful assistant."   ← identical → cache hit
```

### 2. Put stable content first

Order content from most-stable to least-stable:

```
[stable]  CLAUDE.md content          ← changes rarely
[stable]  Skill file content         ← changes rarely
[varying] Project snapshot           ← changes per project
[varying] File contents being edited ← changes per turn
[varying] User message               ← changes every turn
```

### 3. Append, don't insert

When adding new context, append to the end. Inserting in the middle shifts all subsequent tokens → cache miss.

```
# Wrong: insert before existing content
new_context + old_context

# Right: append after existing content  
old_context + new_context
```

### 4. Corrections go last

In CLAUDE.md and AGENTS.md, put behavioral corrections and session-specific notes at the **bottom**, after the stable rules. This preserves the stable prefix.

### 5. Minimum cache window

Most providers require a prefix of ≥1024 tokens to start caching. Keep your stable system content above that threshold.

---

## Session structure (optimal)

```
[System prompt — stable prefix]
  CLAUDE.md rules
  Skills content (if loaded)
  Project snapshot (if present)
  ────────────── cache boundary ──────────────
  Files being edited this turn    ← NOT cached
  
[User message — always new]
  Task description
```

---

## Measuring cache hits

Anthropic API: check `usage.cache_read_input_tokens` in the response.  
A healthy session should show cache reads growing with each turn.

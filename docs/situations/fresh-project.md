# Situation: First session on an unfamiliar codebase

You've joined a new project, inherited a repo, or are diving into an open-source codebase for the first time. The AI has no context. Without a plan, it will read files speculatively for the first 20,000–80,000 tokens before it can help.

---

## The expensive default

Without dont-burn.token, a first session typically looks like this:

```
AI reads: README.md             →  800 tokens
AI reads: package.json          →  300 tokens
AI reads: src/ directory        →  listing
AI reads: src/index.ts          →  400 tokens
AI reads: src/routes/           →  listing
AI reads: src/routes/index.ts   →  600 tokens
AI reads: src/middleware/       →  listing
AI reads: src/middleware/auth.ts →  1,200 tokens
AI reads: src/models/           →  listing
...
[20+ tool calls, ~25,000 tokens just to understand structure]
```

---

## How to run this situation

### Step 1: Generate the snapshot before the session

```bash
python3 ~/dontburn/snapshot/generate.py /path/to/unfamiliar-project
```

This takes 2–10 seconds depending on project size. It walks the directory tree, reads entry points, extracts exported symbols from every source file, and produces a 150–300 line structured summary.

### Step 2: Start the session with the snapshot

```
Read CLAUDE.md, then snapshot/project.md, then skills/index.md. Then wait for my task.
```

### Step 3: Ask orientation questions against the snapshot

```
You: Based on the snapshot, what is the main entry point and how does 
     request handling flow?

AI: Entry point is src/index.ts. It imports createApp from src/app.ts, 
    which chains:
      routes/index.ts → route handlers in controllers/
      middleware/auth.ts → JWT validation
      middleware/error.ts → global error handler
    
    Data layer: models/ → Prisma client → PostgreSQL
    No read needed beyond the snapshot.
```

The AI answered a structural question using only the snapshot — zero additional file reads.

### Step 4: Load the code skill for your first task

```
You: There's a bug where unauthenticated users can access /api/admin routes.

AI: [loads skills/code.md]
    [reads src/routes/index.ts:1-30 — targeted, not the whole file]
    
    src/routes/index.ts:18 — /api/admin routes are registered without 
    the auth middleware:
    
    - router.use('/admin', adminRoutes)
    + router.use('/admin', authenticate, adminRoutes)
```

---

## Token comparison

| Approach | Tokens to first useful answer |
|----------|------------------------------|
| Blind exploration | 20,000–80,000 |
| Snapshot-first | 1,200–2,500 |
| **Saving** | **85–97%** |

---

## What the snapshot does NOT include

- File contents beyond entry points (only signatures)
- Test files (excluded by default)
- Generated/build artifacts
- Configuration values (only config file names)

If the AI needs deeper detail on a specific module, it reads only that module — not the whole project. The snapshot narrows the target; the AI then reads precisely.

---

## Regeneration cadence

For active projects: regenerate when the module structure changes (new service, new controller, dependency added). For stable projects: regenerate monthly.

```bash
# Add to your project's Makefile
snapshot:
	python3 ~/dontburn/snapshot/generate.py . ~/dontburn/snapshot/$(shell basename $(CURDIR)).md
```

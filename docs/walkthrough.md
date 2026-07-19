# User Walkthrough

A complete guide to setting up and using dont-burn.token across different workflows. Follow this end-to-end on your first session, then use the situation guides for specific tasks.

---

## Part 1 — Setup (5 minutes, done once)

### Step 1: Clone the repo

```bash
git clone https://github.com/ca-who-codes/dont-burn.token
```

You'll reference this repo from any project, so place it somewhere permanent:

```bash
# Suggested: home directory
mv dont-burn.token ~/dontburn
```

### Step 2: Verify Python

```bash
python3 --version
# Must be 3.10 or higher. No other dependencies needed.
```

### Step 3: Generate your first snapshot

Point the generator at any project you're about to work in:

```bash
python3 ~/dontburn/snapshot/generate.py /path/to/your/project
```

This creates `~/dontburn/snapshot/project.md` — a compressed map of your project.

**Example output for a medium Node.js project:**

```
# Project Snapshot — my-api
Generated: 2026-06-22  |  Root: /projects/my-api

## Identity
- Type: node
- Language: TypeScript
- Key deps: express, prisma, zod, jose, pino, dayjs
- Scripts: dev, build, test, lint, db:migrate

## Directory tree
src/
  controllers/
  middleware/
  models/
  routes/
  services/
  utils/
tests/
prisma/

## Entry points
### `src/index.ts`
[first 25 lines of the file]

## Module map
### `src/`
**`src/controllers/users.ts`**
  - `export async function getUser(...)`
  - `export async function createUser(...)`
  - `export async function updateUser(...)`
**`src/services/auth.ts`**
  - `export function signToken(...)`
  - `export function verifyToken(...)`
  - `export async function authenticate(...)`
```

Reading this snapshot costs ~500 tokens. Reading the equivalent files blind costs 30,000–80,000 tokens.

### Step 4: Copy CLAUDE.md into your project (optional but recommended)

For Claude Code users, placing `CLAUDE.md` in your project root makes Claude read it automatically on every session.

```bash
cp ~/dontburn/CLAUDE.md /path/to/your/project/CLAUDE.md
```

Or simply symlink it:

```bash
ln -s ~/dontburn/CLAUDE.md /path/to/your/project/CLAUDE.md
```

---

## Part 2 — Starting a session

### The 30-second startup

```bash
bash ~/dontburn/session/init.sh /path/to/your/project
```

The script:
1. Checks if the snapshot is stale (source files changed since last generation)
2. Regenerates it if needed
3. Prints a session brief with counts of skills and corrections
4. Outputs the starter prompt to paste into your AI session

**Example output:**

```
Snapshot up to date

╔═ dontburn session brief ════════════════════════╗
║
║  Project:     my-api
║  Snapshot:    187 lines → /Users/.../snapshot/project.md
║  Skills:      4 available
║  Corrections: 3 accumulated
║
╠═ AI load order ═════════════════════════════════╣
║
║  1. CLAUDE.md              (behavior rules)
║  2. snapshot/project.md    (codebase map)
║  3. skills/index.md        (skill registry)
║  4. session/corrections.md (past learnings)
║
╚═════════════════════════════════════════════════╝

Paste this into your AI session to start:

Read CLAUDE.md, then snapshot/project.md, then skills/index.md, then session/corrections.md. Then wait for my task.
```

### What the AI does with those 4 files

| File | Tokens | What the AI learns |
|------|--------|-------------------|
| CLAUDE.md | ~600 | Response style, tool use rules, load order |
| snapshot/project.md | ~500 | Project structure, entry points, module map |
| skills/index.md | ~100 | Which skills exist (one-line descriptions) |
| session/corrections.md | ~50–300 | Patterns to avoid from past sessions |

**Total startup cost: ~1,250–1,600 tokens.** Without these files, the AI would spend 15,000–50,000 tokens exploring to learn the same things.

---

## Part 3 — During a session

### Using skills

After startup, the AI has read the skill index. When you give it a task, it matches the task to a skill and loads only that file.

**Example conversation:**

```
You: There's a bug in the authentication middleware. JWT tokens are being 
     accepted even after the user's session is revoked.

AI: [reads skills/index.md → matches "code" skill → loads skills/code.md]
    [reads src/middleware/auth.ts:1-40]
    
    src/middleware/auth.ts:28 — Token validation calls verifyToken() but 
    doesn't check the session store. Add a lookup after line 28:
    
    + const session = await sessionStore.get(payload.sub)
    + if (!session) return res.status(401).json({ error: 'session_revoked' })
```

The AI loaded one skill file (~600 tokens) and read one targeted file section (~200 tokens). It did not read the entire codebase.

### Compressing tool outputs

When you're passing external data to the AI — API responses, logs, diffs — compress it first:

```bash
# Compress a large API response
curl -s https://api.github.com/repos/my-org/my-repo/pulls | \
  python3 ~/dontburn/session/compress.py --type json --max-array 5

# Compress build logs
npm run build 2>&1 | python3 ~/dontburn/session/compress.py --type logs

# Compress a PR diff before code review
git diff main...feature-branch | python3 ~/dontburn/session/compress.py --type diff
```

**Before compression (github pulls API response):**
- ~45,000 tokens (full JSON with 100 PRs, each with 60+ fields)

**After compression (max-array 5):**
- ~3,000 tokens (5 PRs, null/empty fields removed)
- Reduction: 93%

### Checking what you're spending

During a session, you can check your input composition to see if the snapshot is helping:

```
You: How much of your context is the snapshot vs other files?

AI: Snapshot: ~500 tokens (3% of context)
    Files read this session: src/middleware/auth.ts — 240 tokens
    Skill loaded: skills/code.md — 580 tokens
    Total session input so far: ~1,320 tokens
```

Compare that to a session without the toolkit: typically 15,000–40,000 tokens in by this point.

---

## Part 4 — After a session

### Log a correction

If you noticed the AI doing something wasteful — restating code, reading unnecessary files, giving a verbose explanation — log it:

```bash
# Append a correction manually
echo "- [$(date +%F)] rule: Don't read package-lock.json when asked about dependencies — read package.json instead. reason: package-lock.json is 50,000 tokens; package.json is 200." >> ~/dontburn/session/corrections.md
```

### Run the learner on a session log (if available)

```bash
python3 ~/dontburn/session/learn.py path/to/session.jsonl
```

The learner detects: preambles, trailing summaries, trailing CTAs, repeated file reads, and oversized tool outputs. It appends corrections to `session/corrections.md`.

### Distill corrections into CLAUDE.md

Once you have 5+ corrections accumulated:

```bash
python3 ~/dontburn/session/learn.py --distill
```

This reads `session/corrections.md`, deduplicates rules by frequency, and appends the top 10 to `CLAUDE.md` as a "Learned corrections" section.

---

## Part 5 — Multi-project setup

### Separate snapshots per project

```bash
# Generate snapshots for multiple projects
python3 ~/dontburn/snapshot/generate.py ~/projects/backend ~/dontburn/snapshot/backend.md
python3 ~/dontburn/snapshot/generate.py ~/projects/frontend ~/dontburn/snapshot/frontend.md
python3 ~/dontburn/snapshot/generate.py ~/projects/data-pipeline ~/dontburn/snapshot/data-pipeline.md
```

Then in your session starter, specify which snapshot to load:

```
Read CLAUDE.md, then snapshot/backend.md, then skills/index.md. Then wait for my task.
```

### Using with different AI tools

**Claude Code:** Copy or symlink `CLAUDE.md` into each project root. Claude reads it automatically.

**Cursor:** Add CLAUDE.md content to `.cursor/rules` or paste into the Cursor system prompt.

**Codex / OpenAI:** Paste CLAUDE.md content as the system message before your task.

**Aider:** Use `--system-prompt ~/dontburn/CLAUDE.md` flag.

**Gemini CLI:** Equivalent to `GEMINI.md` — copy CLAUDE.md there.

**Any API call:**
```python
system = open("~/dontburn/CLAUDE.md").read()
snapshot = open("~/dontburn/snapshot/project.md").read()

messages = [
    {"role": "user", "content": f"{system}\n\n---\n\n{snapshot}\n\nWait for my task."}
]
```

---

## Part 6 — Maintaining the toolkit

### When to regenerate the snapshot

- After adding a new module or package
- After a major refactor
- If the AI is making wrong assumptions about project structure

```bash
python3 ~/dontburn/snapshot/generate.py /path/to/project
```

The `session/init.sh` script does this automatically when it detects source files newer than the snapshot.

### When to run --distill

After every 5–10 sessions, or whenever corrections.md has 10+ entries. Distillation deduplicates rules so CLAUDE.md doesn't grow unbounded.

### Keeping CLAUDE.md stable

The beginning of CLAUDE.md must stay identical between sessions for cache alignment to work. Only append new content to the bottom. The `--distill` command appends a "Learned corrections" section at the bottom, not at the top.

---

## Quick reference

```bash
# First time setup
git clone https://github.com/ca-who-codes/dont-burn.token ~/dontburn

# Every new project
python3 ~/dontburn/snapshot/generate.py /my/project

# Every session start
bash ~/dontburn/session/init.sh /my/project

# Compress before pasting to AI
cat big-file.json | python3 ~/dontburn/session/compress.py --type json
cat server.log    | python3 ~/dontburn/session/compress.py --type logs
git diff          | python3 ~/dontburn/session/compress.py --type diff

# After session
python3 ~/dontburn/session/learn.py session.log
python3 ~/dontburn/session/learn.py --distill   # every 5-10 sessions
```

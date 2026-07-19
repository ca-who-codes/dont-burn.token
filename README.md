# dont-burn.token

> Stop wasting money on tokens your AI never needed to read.

A zero-dependency toolkit that cuts token consumption in AI coding sessions by 40–90% — without changing how you work. Drop it into any project, run one command, and every session becomes leaner.

---

## The problem

When you ask an AI agent to do something in your codebase, it doesn't know what to read. So it reads everything it might need — entire files to find one function, raw API responses with 200 null fields, verbose answers that restate what you just said, the same file three times because it forgot it read it.

On a typical debugging session, 60–80% of the tokens consumed contribute nothing to the answer. You're paying for the AI's exploration, not its thinking.

---

## What this does

| Component | What it saves | How |
|-----------|--------------|-----|
| `CLAUDE.md` | Response bloat | Behavioral rules: no preambles, diffs not full files |
| `skills/` | Skill mismatch | Lazy-load skill files — read descriptions first, full content only on match |
| `snapshot/generate.py` | Blind exploration | Pre-built project map: AI reads a 200-line index instead of 50 files |
| `session/compress.py` | Tool output noise | SmartCrusher for JSON/logs/diffs: drops nulls, truncates arrays |
| `session/learn.py` | Repeated mistakes | Mines sessions for waste patterns, writes corrections to CLAUDE.md |
| `config/cache-align.md` | Cache misses | Stable prompt prefix → provider KV cache hits → 40–90% input cost cut |

---

## Quick start

```bash
git clone https://github.com/ca-who-codes/dont-burn.token
cd dont-burn.token

# Generate a snapshot of your project
python snapshot/generate.py /path/to/your/project

# Bootstrap an AI session
bash session/init.sh /path/to/your/project
```

Paste the output line into your AI session and you're running lean.

---

## How to use in a session

### Option 1 — Claude Code (automatic)

Because `CLAUDE.md` is in the repo root, Claude Code reads it automatically at session start. Clone this repo into your project or copy `CLAUDE.md` into any project root.

### Option 2 — Manual paste

Copy the starter prompt from `session/init.sh` output and paste it as your first message:

```
Read CLAUDE.md, then snapshot/project.md, then skills/index.md, then session/corrections.md. Then wait for my task.
```

### Option 3 — Compress tool outputs inline

```bash
# Before passing a large API response to the AI
curl -s https://api.example.com/data | python session/compress.py --type json

# Before sending logs
cat server.log | python session/compress.py --type logs

# Before asking for a code review
git diff | python session/compress.py --type diff
```

---

## Skills — lazy loading

Instead of loading context for every possible task, skills are loaded only when needed.

```
skills/index.md   ← AI reads this first (one-line descriptions)
skills/code.md    ← loaded when: coding, debugging, refactoring
skills/web.md     ← loaded when: browser automation, HTTP, scraping
skills/data.md    ← loaded when: SQL, pandas, data analysis
skills/write.md   ← loaded when: docs, commits, specs, emails
```

Reading the index costs ~100 tokens. Loading an unneeded full skill costs 500–2000 tokens. The index pays for itself on the first decision.

---

## Snapshot — map before explore

```bash
# Build a compressed project map
python snapshot/generate.py /path/to/project

# Output: snapshot/project.md (~200 lines)
# Contains: identity, dependency list, directory tree, entry points, module map
# Replaces: 50+ file reads worth of blind exploration
```

The snapshot is regenerated automatically by `session/init.sh` when source files change.

---

## Cache alignment

The `config/cache-align.md` guide explains how to structure your prompts so the provider KV cache hits on every turn. The short version:

- Keep the beginning of your system prompt identical across turns
- Append new context to the end, never insert in the middle
- Stable prefix ≥ 1024 tokens → cache kicks in → you pay ~10% of normal input cost on cached tokens

On a 10-turn session with a 5,000-token context, this saves roughly 45,000 cached tokens per session.

---

## Session learning

After each session, the AI may have wasted tokens in patterns that will repeat. `session/learn.py` finds them:

```bash
# Analyze a session log
python session/learn.py session.jsonl

# Distill accumulated corrections into CLAUDE.md
python session/learn.py --distill
```

Detected patterns: preambles, trailing summaries, repeated file reads, oversized tool outputs, unnecessary CTAs.

---

## Situation walkthroughs

- [Fresh project — first session on an unfamiliar codebase](docs/situations/fresh-project.md)
- [Debugging a production issue](docs/situations/debugging.md)
- [Reviewing a pull request](docs/situations/code-review.md)
- [Data analysis and SQL](docs/situations/data-analysis.md)
- [Browser automation and scraping](docs/situations/browser-tasks.md)
- [Navigating a large codebase](docs/situations/large-codebase.md)

---

## Research and methodology

See [docs/research.md](docs/research.md) for the full breakdown of where tokens go, how each component saves them, and the expected savings by session type.

---

## Structure

```
CLAUDE.md                    ← behavior rules (auto-read by Claude Code)
AGENTS.md                    ← multi-agent version
skills/
  index.md                   ← lazy skill registry
  code.md / web.md / data.md / write.md
snapshot/
  generate.py                ← project map generator
session/
  init.sh                    ← session bootstrapper
  compress.py                ← SmartCrusher for JSON, logs, diffs, code
  learn.py                   ← session waste analyzer
  corrections.md             ← accumulated behavioral corrections
config/
  output-shaper.md           ← verbosity + effort rules
  cache-align.md             ← KV-cache alignment guide
docs/
  research.md                ← evidence and methodology
  walkthrough.md             ← full user walkthrough
  situations/                ← per-scenario guides
```

---

## Compatibility

Works with any AI that reads markdown context: Claude Code, Cursor, Codex, Gemini CLI, Aider, Amp, and any model accessed via API.

The Python scripts require Python 3.10+. No external dependencies.

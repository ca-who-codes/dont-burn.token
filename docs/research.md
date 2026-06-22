# Research — Where Tokens Go and How to Recover Them

This document explains the methodology behind dont-burn.token, the evidence for each saving, and what realistic outcomes look like across different session types.

---

## 1. How tokens are spent in a typical session

An AI coding session burns tokens in two directions: **input** (what the model reads) and **output** (what it writes back). Both cost money, but differently.

### Input token sources

| Source | Share of input | Typical session |
|--------|---------------|-----------------|
| System prompt / CLAUDE.md | 3–8% | 1,000–5,000 tokens |
| Files read | 35–65% | 10,000–80,000 tokens |
| Tool outputs (grep, API, tests) | 15–35% | 5,000–40,000 tokens |
| Conversation history | 10–25% | 3,000–30,000 tokens |
| Repeated reads (redundancy) | 10–30% | 3,000–30,000 tokens |

The "repeated reads" row is pure waste: the same file or tool output read multiple times because the model lost track of what it already had.

### Output token sources

| Source | Share of output | Typical session |
|--------|----------------|-----------------|
| Actual answers / code | 55–70% | 3,000–15,000 tokens |
| Preambles ("Great, let me...") | 5–15% | 300–3,000 tokens |
| Trailing summaries | 5–15% | 300–3,000 tokens |
| Restated code (already in context) | 10–25% | 600–5,000 tokens |
| Unnecessary CTAs | 2–5% | 100–500 tokens |

On Anthropic's Sonnet 4.6, output costs 5× input. Preambles and summaries that add 20% to response length cost more than 100% more efficient input loading.

---

## 2. What each component saves

### CLAUDE.md — behavioral rules

**Mechanism:** Explicit instructions prevent the three most expensive output patterns.

| Pattern eliminated | Tokens saved per occurrence | Occurrences per session |
|--------------------|---------------------------|------------------------|
| Preamble ("Great! Let me...") | 15–40 tokens | 8–20 |
| Trailing summary | 50–200 tokens | 5–15 |
| Restated code | 200–2,000 tokens | 3–10 |

**Expected session saving:** 1,500–20,000 output tokens  
**In dollars (Sonnet 4.6 at $15/M output):** $0.02–$0.30 per session  
**Compound effect:** In a 50-session month, $1–$15 saved on output alone.

---

### Skills — lazy loading

**Mechanism:** The AI reads one-line descriptions (skills/index.md, ~100 tokens) and loads a full skill file only when the task matches. Without lazy loading, some agents preload all context "just in case."

| Loading strategy | Tokens loaded | Tokens actually used |
|-----------------|--------------|---------------------|
| Eager (load all skills) | 3,000–6,000 | 500–1,500 |
| Lazy (load on match) | 100–1,500 | 100–1,500 |

**Expected session saving:** 1,500–4,500 input tokens per session  
**In dollars:** $0.004–$0.015 per session (small but free, zero effort)

---

### Snapshot — project map

**Mechanism:** The AI reads a 200-line structured summary instead of exploratory file reads. This is the highest-leverage component for sessions involving unfamiliar codebases.

**Evidence from headroom benchmarks (codebase exploration workload):**

| Approach | Tokens consumed |
|----------|----------------|
| Blind exploration (no snapshot) | 78,502 |
| Snapshot-first exploration | 41,254 |
| **Saving** | **47% (37,248 tokens)** |

For a code search task with 100 results, headroom reported 10,144 → 1,260 tokens — an 88% reduction when the model had a structured index to work from instead of raw grep output.

**Expected session saving:** 10,000–60,000 input tokens for exploration-heavy sessions  
**In dollars:** $0.03–$0.18 per session (Sonnet 4.6 at $3/M input)

---

### compress.py — tool output SmartCrusher

**Mechanism:** Removes signal-to-noise from tool outputs before they enter context.

#### JSON compression

Most API and database tool outputs contain:
- Null/empty fields (average: 15–40% of all fields)
- Oversized arrays (pagination, result sets)
- Internal metadata irrelevant to the task

A typical 10KB API response compresses to 2–4KB with no information loss for the task at hand.

| Content type | Typical reduction |
|-------------|------------------|
| JSON with many null fields | 25–45% |
| JSON with long arrays (>20 items) | 40–70% |
| Nested JSON (3+ levels) | 30–60% |

#### Log compression

Server logs are typically 80–95% noise: health checks, debug lines, routine GETs. Signal lines (errors, warnings, stack traces) are 5–20% of total volume.

| Log type | Lines kept | Token reduction |
|----------|-----------|----------------|
| Web server logs | 5–20% | 80–95% |
| Application logs | 20–40% | 60–80% |
| Build output | 10–30% | 70–90% |

#### Diff compression

A unified diff of a 200-line file change passes ~400 lines of context markers through. After compression (skip identical hunks, keep ±3 lines context), a typical diff shrinks by 40–70%.

---

### Cache alignment — KV-cache hits

**Mechanism:** Provider KV caches save the computed attention for a prompt prefix. If the prefix matches on the next turn, the provider reuses it. Anthropic charges 10% of normal input cost for cache-read tokens.

**Savings model (10-turn session, 5,000-token stable prefix):**

| Turn | Tokens sent | Without cache | With cache (90% discount) |
|------|-------------|--------------|--------------------------|
| 1 | 5,000 + 200 | $0.0156 | $0.0156 (cold) |
| 2 | 5,000 + 300 | $0.0159 | $0.0024 (90% off) |
| 3 | 5,000 + 400 | $0.0162 | $0.0026 |
| ... | ... | ... | ... |
| 10 | 5,000 + 1,100 | $0.0183 | $0.0033 |
| **Total** | | **$0.1656** | **$0.0440** |

**Saving: 73% of input cost on a 10-turn session.** This is the highest ROI component — it requires only that you keep the system prompt stable, which costs nothing.

**Condition for cache hit:** Prefix must be ≥ 1,024 tokens and identical (character-level) to the previous turn's prefix.

---

### session/learn.py — behavioral correction

**Mechanism:** Waste patterns repeat. Once identified and written to corrections.md, the AI avoids them in future sessions. The savings compound.

A single preamble ("Sure! Let me help you with that. First, I'll read the relevant files...") costs 30–60 tokens and provides zero value. Across 20 responses per session × 50 sessions per month = 30,000–60,000 wasted output tokens monthly from this pattern alone.

**Expected monthly saving from learn.py (after 5 sessions):** 20,000–80,000 output tokens  
**In dollars:** $0.30–$1.20/month ongoing

---

## 3. Total expected savings by session type

### Debugging a production issue (1–2 hour session)

Without dont-burn.token:
- Reads 15–30 files to trace the bug
- Gets verbose responses with full file reprints
- Processes raw 50KB log output
- **Typical: 150,000–400,000 tokens**

With dont-burn.token:
- Reads snapshot, then targeted files (3–8 reads)
- Compressed logs (5,000 → 800 tokens)
- Terse responses, diffs only
- **Typical: 40,000–120,000 tokens**

**Saving: 55–75%**  
**In dollars (Sonnet 4.6):** $0.40–$2.50 saved per debugging session

---

### Code review of a medium PR (30–60 min session)

Without dont-burn.token:
- Reads every changed file in full
- Verbose review with restated code
- **Typical: 80,000–200,000 tokens**

With dont-burn.token:
- Reads diff (compressed) + only directly changed modules
- Review in `file:line — issue` format
- **Typical: 20,000–60,000 tokens**

**Saving: 60–75%**

---

### Exploring a new codebase (first session)

Without dont-burn.token:
- Sequential file reads to understand structure
- 20–50 `ls`, `cat`, `grep` calls
- **Typical: 100,000–300,000 tokens**

With dont-burn.token:
- Generate snapshot once (costs ~500 tokens to generate locally)
- AI reads 200-line snapshot instead
- Targeted reads for specific questions
- **Typical: 20,000–80,000 tokens**

**Saving: 70–80%**

---

### Data analysis session (2–3 hours)

Without dont-burn.token:
- Full DataFrame prints (1,000 rows × 20 columns)
- Verbose SQL queries with full result sets
- Repeated schema reads
- **Typical: 200,000–600,000 tokens**

With dont-burn.token:
- Schema only (no data), `df.head(5)` previews
- Compressed JSON responses
- LIMIT 1000 by default, count-first workflow
- **Typical: 40,000–120,000 tokens**

**Saving: 70–80%**

---

## 4. Cost model at scale

Monthly estimate for a developer doing 5 coding sessions/week, 1-hour average:

| Scenario | Monthly tokens (no toolkit) | Monthly tokens (with toolkit) | Monthly saving |
|----------|---------------------------|------------------------------|---------------|
| Lightweight (simple fixes) | 5M | 2M | $9 |
| Moderate (feature work) | 15M | 5M | $30 |
| Heavy (complex debugging) | 40M | 10M | $90 |

Pricing: Sonnet 4.6 — $3/M input, $15/M output, cache-read $0.30/M.  
Conservative assumption: 60% input / 40% output split.

---

## 5. What this toolkit does NOT do

- It does not install a proxy or intercept your API calls
- It does not compress content automatically — you choose when to run compress.py
- It does not guarantee savings — token consumption depends on task complexity
- It is not a replacement for model selection (Haiku is cheaper than Sonnet for simple tasks)
- Snapshot freshness degrades as code changes — regenerate after significant refactors

---

## 6. Sources and methodology

Token savings figures for snapshot-based exploration are drawn from headroom-ai's published benchmarks (codebase exploration: 78,502 → 41,254 tokens, 47% saving; code search: 17,765 → 1,408, 92% saving).

Cache alignment savings are calculated from Anthropic's published pricing: cache-read tokens cost $0.30/M vs $3/M for normal input — a 90% discount. The 1,024-token minimum prefix requirement is documented in the Anthropic API reference.

Output token percentages (preambles, summaries) are estimates based on analysis of Claude Code session transcripts from this repo's session/learn.py pattern detection, cross-referenced with headroom's output shaper documentation.

All dollar figures use Sonnet 4.6 pricing as of June 2026.

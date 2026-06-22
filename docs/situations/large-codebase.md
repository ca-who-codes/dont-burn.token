# Situation: Navigating a large codebase

A large codebase (100K+ lines, 500+ files) is the hardest case for token efficiency. There is no shortcut that reads enough to be useful without burning context. The only winning strategy is to never read more than you need.

---

## The failure mode

Without a plan, the AI runs a sequence of progressively deeper reads trying to "understand" the codebase:

```
AI reads: README.md                          →  1,200 tokens
AI reads: src/ (directory listing)           →  200 tokens
AI reads: src/core/ (directory listing)      →  300 tokens
AI reads: src/core/index.ts                  →  800 tokens
AI reads: src/core/engine.ts                 →  4,200 tokens (imports 12 modules)
AI reads: src/core/scheduler.ts              →  3,100 tokens
AI reads: src/core/worker.ts                 →  2,800 tokens
... [reads 15 more files trying to understand the dependency chain]

Context window now: 60,000 tokens
AI still hasn't identified which file to change.
```

On a 200K-line codebase, this can exhaust the context window before the AI finds the right file.

---

## Strategy: map first, read never

The snapshot covers the module map without reading implementations. Combined with grep-based symbol lookup, you can navigate a million-line codebase without reading more than 3–5 files.

### Step 1: Generate the snapshot

```bash
python3 ~/dontburn/snapshot/generate.py /path/to/large-project
```

For large projects, the snapshot may take 10–30 seconds. It reads only signatures (function names, class names, exports) — not implementations. A 500,000-line codebase typically produces a 400–600 line snapshot.

### Step 2: Navigate with grep, not reads

```
You: I need to change how retries are handled for failed API calls.
     The module map shows a `RetryPolicy` type in src/http/client.ts.
     Confirm where retry logic is implemented.

AI: [runs: grep -n "retry\|RetryPolicy" src/http/ --include="*.ts"]
    
    src/http/client.ts:88:  applyRetry(policy: RetryPolicy, attempt: number)
    src/http/client.ts:110: this.retryPolicy = config.retry ?? defaultRetryPolicy
    src/http/retry.ts:12:   export class RetryPolicy { ... }
    src/http/retry.ts:45:   shouldRetry(error: HttpError, attempt: number): boolean

    Reads only: src/http/retry.ts:40-60 (20 lines)
```

One grep (100 tokens). One targeted read (200 tokens). Done.

### Step 3: Read only the change site

```
You: Read only the shouldRetry function and the defaultRetryPolicy.

AI: [reads src/http/retry.ts:45-80, src/http/retry.ts:12-20]

    shouldRetry currently retries on all 5xx errors up to 3 times with 
    exponential backoff (1s, 2s, 4s). It does not retry 429 (rate limit) — 
    it should, but with the Retry-After header as the delay.

    src/http/retry.ts:52-58:
    - if (error.status >= 500) return attempt < this.maxAttempts
    + if (error.status >= 500 || error.status === 429) {
    +   if (error.status === 429 && error.headers['retry-after']) {
    +     this.delay = parseInt(error.headers['retry-after']) * 1000
    +   }
    +   return attempt < this.maxAttempts
    + }
```

2 reads, targeted. ~400 tokens for the reads. Fix is precise.

---

## Token comparison

| Approach | Files read | Input tokens |
|----------|-----------|-------------|
| Exploratory (no snapshot) | 15–30 files | 50,000–120,000 |
| Snapshot + grep + targeted read | 1–3 files | 3,000–8,000 |
| **Saving** | **90%+ files skipped** | **90–97%** |

---

## The snapshot module map in practice

The snapshot's module map section looks like this for a large project:

```
### `src/http/`
**`src/http/client.ts`**
  - `export class HttpClient`
  - `export function createClient(...)`
  - `export type HttpConfig`
**`src/http/retry.ts`**
  - `export class RetryPolicy`
  - `export const defaultRetryPolicy`
  - `shouldRetry(...)`
  - `applyRetry(...)`
**`src/http/interceptors.ts`**
  - `export function addAuthHeader(...)`
  - `export function logRequest(...)`
  - `export function handleErrors(...)`

### `src/core/`
**`src/core/engine.ts`**
  - `export class Engine`
  - `export function createEngine(...)`
...
```

From this, you can answer "where is retry logic?" without reading a single implementation file. The answer is `src/http/retry.ts` — visible directly from the map.

---

## Monorepo navigation

For monorepos with multiple packages, generate one snapshot per package:

```bash
# One command for all packages
for pkg in packages/*/; do
  python3 ~/dontburn/snapshot/generate.py "$pkg" \
    ~/dontburn/snapshot/$(basename "$pkg").md
done
```

Then load only the snapshot for the package you're working in:

```
Read CLAUDE.md, then snapshot/api-gateway.md. I'm working in packages/api-gateway.
```

---

## When the snapshot isn't enough

For questions that require understanding runtime behavior (not structure), the snapshot won't help:

- "Why does this function return null sometimes?" → you need to read the function body
- "How does data flow from A to B through C, D, E?" → you need to trace call graphs

For these, use the snapshot to find the right files, then read only those files:

```
You: The snapshot shows Engine.process() calls scheduler.queue(). 
     I need to understand how items move from the queue to workers.
     
     Read only: src/core/scheduler.ts (the queue method) and 
     src/core/worker.ts (the dequeue logic).

AI: [reads 2 targeted files, ~80 lines total]
    ...
```

Guided reads are fine. Exploratory reads are the token drain.

---

## Practical limits

| Codebase size | Snapshot size | Snapshot generation time |
|--------------|--------------|------------------------|
| Small (<10K lines) | 50–100 lines | <1 second |
| Medium (10K–100K lines) | 100–300 lines | 1–5 seconds |
| Large (100K–1M lines) | 300–600 lines | 5–30 seconds |
| Very large (1M+ lines) | 600–800 lines | 30–120 seconds |

The snapshot scales to any codebase. The module map truncates at 20 files per directory to stay readable.

---

## Working with generated code

Large codebases often have generated files (protobuf bindings, GraphQL types, ORM models). These are typically the highest-token-count files and the least useful to read.

Add them to SKIP_DIRS in `snapshot/generate.py` or exclude them from grep patterns:

```bash
# Exclude generated files from grep
grep -rn "RetryPolicy" src/ --include="*.ts" --exclude-dir="generated" --exclude-dir="__generated__"
```

Never paste generated files to the AI. They are verbose, machine-produced, and the AI already knows the pattern from the schema.

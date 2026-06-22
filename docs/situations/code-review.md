# Situation: Reviewing a pull request

Code review is one of the highest token-burn tasks: the AI reads every changed file in full, then writes verbose commentary. A 20-file PR can cost 100,000–300,000 tokens without discipline.

---

## The expensive default

```
PR: Add user authentication (22 files changed)

AI reads: src/auth/index.ts        → 3,200 tokens (full file)
AI reads: src/auth/jwt.ts          → 1,800 tokens (full file)
AI reads: src/middleware/auth.ts   → 2,100 tokens (full file)
...22 files...                     → ~55,000 tokens total
AI responds:
  "Thank you for sharing this PR! I'll now provide a comprehensive 
   review of the authentication implementation...
   
   1. src/auth/index.ts
      This file contains the main authentication logic. Overall, the 
      implementation looks solid. Here are my observations:
      - The createToken function on line 24 uses HS256 which is 
        appropriate for this use case..."
                                   → 8,000 token verbose review

Total: ~63,000 tokens
```

---

## How to run this situation

### Step 1: Get a compressed diff

```bash
# For a GitHub PR (using gh CLI)
gh pr diff 142 | python3 ~/dontburn/session/compress.py --type diff

# For a local branch
git diff main...feature/auth | python3 ~/dontburn/session/compress.py --type diff

# For staged changes
git diff --staged | python3 ~/dontburn/session/compress.py --type diff
```

The diff compressor keeps:
- File headers (`--- a/file.ts`, `+++ b/file.ts`)
- All added lines (`+`)
- All removed lines (`-`)
- ±3 lines of context around changes
- Unchanged hunks replaced with `[... N unchanged lines ...]`

A 500-line diff of a 20-file PR typically compresses to 200–280 lines.

### Step 2: Load the code skill

```
Read CLAUDE.md, then skills/code.md.

[paste compressed diff]

Review this for: correctness bugs, security issues, and obvious performance problems. Skip style preferences.
```

### Step 3: The AI reviews surgically

With the code skill's review format active:

```
AI: src/auth/jwt.ts:34 — HS256 with a hardcoded secret. Secret must come from 
    environment variable; rotate on breach.

    src/middleware/auth.ts:18 — No expiry check after decoding token. A decoded 
    token with exp in the past will be accepted.

    src/auth/index.ts:67 — Password compared with ==, not bcrypt.compare(). 
    Timing attack vulnerability.

    3 issues found. No performance concerns in the changed paths.
```

No preamble. No "overall the PR looks good." Each finding is `file:line — issue`. Actionable, dense, complete.

---

## Token comparison

| Approach | Input | Output | Total |
|----------|-------|--------|-------|
| Full file reads + verbose review | 55,000 | 8,000 | 63,000 |
| Compressed diff + code skill | 8,000 | 400 | 8,400 |
| **Saving** | **85%** | **95%** | **87%** |

---

## Review prompt templates

### Security-focused review

```
Review this diff for security issues only:
- Injection vulnerabilities (SQL, command, LDAP)
- Authentication/authorization bypass
- Secrets or credentials in code
- Missing input validation at trust boundaries

Format: file:line — description. Skip everything else.
```

### Performance-focused review

```
Review this diff for performance issues:
- N+1 queries
- Missing indexes on filtered columns
- Unbounded loops or O(n²) operations
- Synchronous I/O in async paths

Format: file:line — description. Skip style and correctness.
```

### Quick sanity check

```
Does this diff introduce any obvious bugs or break existing behavior? 
One sentence per issue. Skip nitpicks.
```

---

## For large PRs (50+ files)

Break it into passes:

```bash
# Pass 1: critical path files only
git diff main...feature --name-only | grep -E "auth|payment|security" | \
  xargs git diff main...feature -- | \
  python3 ~/dontburn/session/compress.py --type diff

# Pass 2: everything else
git diff main...feature --name-only | grep -vE "auth|payment|security" | \
  xargs git diff main...feature -- | \
  python3 ~/dontburn/session/compress.py --type diff
```

One session per pass. The AI focuses where it matters.

---

## What not to ask the AI to review

- Style and formatting (use a linter — ESLint, prettier, ruff)
- Test coverage (use a coverage tool — nyc, pytest-cov)
- Documentation completeness (separate doc review if needed)
- Dependency versions (use a dependency scanner — Dependabot, Snyk)

These are zero-value review requests. They burn tokens on work that automated tools do better and faster.

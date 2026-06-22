# Situation: Browser automation and web scraping

Web tasks have a unique token problem: raw HTML. A single modern web page can be 50,000–500,000 characters of markup, styles, and scripts. Passing raw HTML to an AI for "find the login button" costs 15,000–120,000 tokens for something that takes 200.

---

## The expensive default

```
Task: Log into dashboard.example.com and get the account balance.

AI approach (no toolkit):
  Fetch page HTML                    → 45,000 tokens raw HTML
  AI response: "I can see the HTML.
    The login form appears to be at..."  → 2,000 token analysis
  Fetch next page HTML               → 38,000 tokens
  [3 more page fetches]              → 120,000 tokens total

Cost: $0.38 for a task that takes 30 seconds manually
```

---

## The accessibility-tree approach

Agent-browser's key insight: AI agents don't need HTML. They need an **accessibility tree** — a structured list of interactive elements with symbolic refs. A full page's accessibility tree is 200–400 tokens. The same page's HTML is 15,000–120,000 tokens.

```bash
# Install once
npm install -g agent-browser && agent-browser install

# The core loop
agent-browser open https://dashboard.example.com
agent-browser snapshot -i              # interactive elements only
agent-browser click @e3                # act on refs from snapshot
agent-browser snapshot -i              # re-snapshot after navigation
```

**Snapshot output (200 tokens vs 45,000 for raw HTML):**

```
Page: Sign In — Dashboard
URL: https://dashboard.example.com/login

@e1 [heading] "Sign In"
@e2 [input type="email"] placeholder="Email address"
@e3 [input type="password"] placeholder="Password"
@e4 [button type="submit"] "Sign In"
@e5 [link] "Forgot password?"
```

The AI fills `@e2`, fills `@e3`, clicks `@e4`. Done. No HTML ever entered context.

---

## Token comparison

| Method | Tokens per page interaction |
|--------|---------------------------|
| Raw HTML fetch | 15,000–120,000 |
| WebFetch (markdown-converted) | 3,000–20,000 |
| Accessibility tree snapshot (-i) | 200–400 |
| **Saving over raw HTML** | **97–99%** |

---

## How to run this situation

### Step 1: Load the web skill

```
Read CLAUDE.md, then skills/web.md. Then wait.
```

The web skill encodes: use accessibility snapshots, extract only relevant sections, truncate output before reasoning.

### Step 2: Use the right tool for the task

**For browser automation (logins, clicks, form fills):**
```bash
# Use agent-browser with -i flag (interactive elements only)
agent-browser open https://example.com
agent-browser snapshot -i
```

**For data extraction from public pages:**
```bash
# Fetch and pipe through compress before pasting to AI
curl -s https://example.com/data | \
  python3 -c "
import sys, re
html = sys.stdin.read()
# Strip scripts, styles, keep text
text = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.DOTALL)
text = re.sub(r'<[^>]+>', ' ', text)
text = re.sub(r'\s+', ' ', text).strip()
print(text[:5000])  # first 5000 chars of visible text
"
```

**For API testing:**
```bash
# Compress response before AI reasoning
curl -s https://api.example.com/endpoint | \
  python3 ~/dontburn/session/compress.py --type json --max-array 5
```

### Step 3: Extract the signal, not the page

Instead of asking the AI to process a full page, extract just the element you need:

**High-token approach:**
```
You: [pastes 40,000 token HTML]
     Find the account balance on this page.
```

**Low-token approach:**
```
You: Page title: "My Account — Dashboard"
     Visible text (truncated to relevant section):
     
     Account Overview
     Balance: $4,821.50
     Available credit: $18,000.00
     Next payment: Jul 15, 2026 — $250 minimum
     
     What is the current balance and when is the next payment?
```

You extracted the relevant text yourself (2-second browser inspection) and passed 60 tokens instead of 40,000.

---

## Scraping workflow

### Small scrape (1–10 pages)

```bash
# 1. Fetch page
curl -s https://example.com/products > page.html

# 2. Extract visible text
cat page.html | python3 -c "
import sys, re, html as htmllib
h = sys.stdin.read()
h = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', h, flags=re.DOTALL)
h = re.sub(r'<[^>]+>', '\n', h)
h = htmllib.unescape(h)
lines = [l.strip() for l in h.splitlines() if l.strip()]
print('\n'.join(lines[:200]))  # cap at 200 lines
"

# 3. Paste extracted text to AI, not raw HTML
```

### Large scrape (100+ pages)

For large scrapes, don't loop the AI. Write the extraction logic once, run it yourself:

```
You: I need to scrape product names and prices from example.com/products 
     (100 pages, same structure). Here's the HTML of one page:

     [paste ONE page's compressed HTML]

     Write a Python scraper for all 100 pages.
```

The AI writes the scraper from one example. You run it. 100× pages × 40,000 tokens = 4M tokens NOT burned.

---

## WebFetch vs accessibility tree vs raw HTML

| Task | Best tool | Why |
|------|-----------|-----|
| Click a button | `agent-browser snapshot -i + click` | Refs are exact, no HTML needed |
| Fill a form | `agent-browser fill @eN` | Same |
| Extract specific text | `WebFetch` with a precise prompt | Converts HTML to markdown, much smaller |
| Understand page structure | `agent-browser snapshot` (no -i) | Full accessibility tree, structured |
| Write a scraper | Paste ONE page's text excerpt | AI writes code; you run it at scale |
| Test an API | `curl + compress.py` | JSON output, not HTML |

---

## Anti-patterns

| Anti-pattern | Cost | Fix |
|-------------|------|-----|
| Paste raw HTML | 15,000–120,000 tokens | Use accessibility tree or extracted text |
| Fetch entire site to find a link | Thousands of tokens per page | Use `agent-browser snapshot -i` for refs |
| Load page, ask AI what it sees | Full page in context | Extract the specific element first |
| Ask AI to process paginated results | N × page tokens | Write a script, run yourself |

---

## Refs go stale — always re-snapshot

A critical pattern from agent-browser: refs (`@e1`, `@e2`) are assigned fresh on every snapshot. After any click that navigates, any form submit, or any dynamic re-render, old refs point to nothing.

```bash
agent-browser click @e4          # submits login form
agent-browser snapshot -i        # re-snapshot — page changed
agent-browser fill @e7 "query"   # new ref on the new page
```

Never reuse a ref across a page transition. Re-snapshot first.

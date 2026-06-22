---
name: web
description: Browser automation, HTTP requests, web scraping, and API testing. Load this for any task that involves a URL, browser, or network call.
allowed-tools: Bash, WebFetch, Read, Write
---

# Web Skill

## Browser automation (accessibility-tree approach)

Use `agent-browser` when available. Accessibility-tree snapshots cost ~200–400 tokens vs ~10,000 for raw HTML.

```bash
agent-browser open <url>
agent-browser snapshot -i              # interactive elements only (preferred)
agent-browser click @e3                # act on refs from snapshot
agent-browser snapshot -i              # re-snapshot after any page change
```

Refs go stale after every navigation or dynamic update — always re-snapshot before the next interaction.

Use `-i` (interactive only) by default. Use full `snapshot` only when you need non-interactive content.

## HTTP / API testing

```bash
curl -s -o /dev/null -w "%{http_code}" <url>           # status check
curl -s <url> | python3 -m json.tool | head -50        # JSON preview (50 lines)
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"key":"value"}' <url>                           # POST
```

Truncate curl output before reasoning — never pipe 10,000 lines of HTML into context.

## Scraping

1. Fetch the page (`WebFetch` or `curl`)
2. Extract only the relevant section (CSS selector or line range)
3. Return the extracted data, not the full page

## Output rules

- Show extracted data, not the full response
- For JSON: print only the fields relevant to the task
- For HTML: extract text content, not markup
- Truncate at 50 lines unless completeness is the task

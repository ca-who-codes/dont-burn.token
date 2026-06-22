# Situation: Data analysis and SQL

Data sessions are token traps. Raw DataFrames have thousands of rows. SQL result sets have hundreds of columns. JSON API responses from data warehouses return deeply nested objects with metadata. Without compression, an analysis session can burn 500,000+ tokens on data the AI never needed to see row-by-row.

---

## The expensive default

```
Task: Analyze why our conversion rate dropped last week.

AI reads: events.csv (45,000 rows × 18 columns)  → 480,000 tokens
AI prints: df.describe() output                   → 3,000 tokens  
AI runs: SQL returning 1,200 rows                 → 28,000 tokens
AI responds: "Great question! Let me walk through this 
  analysis step by step. First, I loaded the data..."
                                                  → 2,000 token preamble

Total: ~513,000 tokens
```

At Sonnet 4.6 pricing: $7.70 for one analysis session.

---

## How to run this situation

### Step 1: Load the data skill

```
Read CLAUDE.md, then skills/data.md. Then wait.
```

The data skill enforces: schema only (no data), `df.head(5)` previews, `LIMIT 1000` in SQL, count-first workflow.

### Step 2: Give context, not data

Instead of pasting a CSV, describe the schema and ask questions:

```
You: Database schema:
     events(id, user_id, event_type, ts, session_id, device, country, value)
     users(id, plan, created_at, churned_at)
     
     Conversion rate dropped from 3.2% to 1.8% between June 14-20.
     Write a SQL query to find where the drop happened.

AI: [no data read — generates SQL directly from schema]

SELECT 
  DATE(ts) as date,
  device,
  country,
  COUNT(DISTINCT session_id) as sessions,
  COUNT(DISTINCT CASE WHEN event_type = 'purchase' THEN user_id END) as conversions,
  ROUND(100.0 * COUNT(DISTINCT CASE WHEN event_type = 'purchase' THEN user_id END) 
    / COUNT(DISTINCT session_id), 2) as conversion_rate
FROM events
WHERE ts BETWEEN '2026-06-14' AND '2026-06-20'
GROUP BY date, device, country
ORDER BY date, conversion_rate ASC
LIMIT 1000;
```

0 data tokens read. The AI worked from the schema description (~80 tokens) alone.

### Step 3: Share only the relevant query result

After running the SQL, compress the output before sharing:

```bash
# Compress a SQL result set (JSON format from most BI tools)
cat query_result.json | python3 ~/dontburn/session/compress.py --type json --max-array 10
```

Or paste only the meaningful rows:

```
You: Top findings from the query (showing top 5 by drop):

date        device   country  sessions  conversions  rate
2026-06-17  mobile   IN       8,421     42           0.50%   ← was 3.1%
2026-06-17  mobile   BR       3,102     18           0.58%   ← was 2.8%
2026-06-18  mobile   IN       9,103     45           0.49%
2026-06-18  mobile   BR       3,401     21           0.62%
2026-06-17  desktop  IN       2,100     63           3.00%   ← normal

What does this tell us?
```

Instead of 1,200 rows, you passed 5 rows. The pattern is clear: mobile traffic from India and Brazil dropped sharply. The AI identifies this immediately.

---

## Token comparison

| Approach | Input tokens | Output tokens | Total |
|----------|-------------|--------------|-------|
| Full CSV + raw results | 510,000 | 5,000 | 515,000 |
| Schema + compressed results | 800 | 1,500 | 2,300 |
| **Saving** | **99.8%** | **70%** | **99.6%** |

**In dollars:** $7.70 → $0.03. This is the highest-leverage situation in the toolkit.

---

## Patterns by analysis type

### Exploratory analysis (EDA)

```
You: Schema: orders(id, user_id, total, status, created_at, region, sku_count)

     df.describe() output:
     total: mean=127, std=89, min=5, max=2400, 25%=52, 75%=180
     sku_count: mean=3.2, std=2.1, min=1, max=47
     
     df.value_counts('status'): completed=72%, pending=18%, failed=10%
     df.value_counts('region'): NA=45%, EU=32%, APAC=23%

     What analysis should I run to understand revenue concentration?
```

You passed summary statistics, not the underlying data. The AI has enough to suggest: Lorenz curve for revenue concentration, cohort analysis by region, failure rate by sku_count bucket.

### SQL debugging

```
You: This query runs in 45 seconds on a 10M row table:

SELECT user_id, COUNT(*) as event_count
FROM events
WHERE ts > NOW() - INTERVAL '30 days'
GROUP BY user_id
HAVING COUNT(*) > 100;

EXPLAIN output:
Seq Scan on events (cost=0.00..285000.00 rows=10000000)
  Filter: (ts > (now() - '30 days'::interval))

What index should I add?

AI: CREATE INDEX events_ts_user_id ON events(ts, user_id);

    The sequential scan is scanning all 10M rows to filter by ts.
    The composite index on (ts, user_id) lets the planner use an index
    range scan for the ts filter and a covering index for the GROUP BY.
```

No data read. Just the EXPLAIN output (~200 tokens).

### Anomaly detection

```
You: Daily revenue for the last 30 days (one line each):
     Jun 1: $42,100, Jun 2: $41,800, ..., Jun 20: $43,200, 
     Jun 21: $12,400, Jun 22: $13,100

     What happened on June 21?

AI: Revenue dropped ~71% (from ~$42K baseline to ~$12.5K) on Jun 21.
    
    Likely causes (in order of probability):
    1. Payment processor outage — check Stripe dashboard for Jun 21
    2. Deployment on Jun 20 that broke checkout — check deploy log
    3. Traffic drop — check session counts for same period
    
    Which of these can you check?
```

Passed as inline text, not a CSV. 30 numbers. Zero file reads.

---

## Anti-patterns to avoid

| Anti-pattern | Problem | Fix |
|-------------|---------|-----|
| `df.to_csv()` then paste | Full dataset in context | Use `df.head(10)` or `df.describe()` |
| `print(df)` | Full DataFrame print | Use `df.shape` + `df.head(5)` |
| `SELECT *` | All columns, all rows | Select needed columns, add LIMIT |
| Paste raw API JSON | Nested objects with metadata | `compress.py --type json` first |
| Run analysis, paste all output | Full verbose output | Extract the key metric, share that |

---

## When you do need full data

For training ML models or statistical tests that require sample representativeness, full data is necessary — but the AI shouldn't see it.

```
You: I need to train a model. Here's the schema. Write the feature 
     engineering code and I'll run it locally.

AI: [writes code without seeing any data]
```

The AI writes code against the schema. You run it. The model trains on full data without it entering the AI's context.

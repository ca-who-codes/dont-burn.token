---
name: data
description: Data analysis, SQL queries, pandas/polars operations, and visualization. Load this for any task that involves datasets, databases, or charts.
allowed-tools: Bash, Read, Write, Edit
---

# Data Skill

## Context loading

Read only:
- Schema files (DDL, models.py, schema.prisma) — not the data itself
- The specific query or transformation being modified
- Sample output (first 10 rows) — never full datasets

## SQL

Write queries to return ≤1000 rows by default. Add `LIMIT 1000` unless the task explicitly needs all rows.

```sql
-- Always use LIMIT during exploration
SELECT col1, col2, COUNT(*)
FROM table
WHERE condition
GROUP BY col1, col2
ORDER BY 3 DESC
LIMIT 1000;
```

For large result sets: run `COUNT(*)` first, then decide if a full scan is needed.

## pandas / polars

```python
# Preview before loading
df.shape       # dimensions
df.dtypes      # types
df.head(5)     # sample

# Filter early — don't load all rows, then filter
df = pd.read_csv(path, usecols=['col1', 'col2'], nrows=1000)
```

Never print a DataFrame with >20 rows unless the task requires it.

## Analysis output format

```
Shape: 45,231 rows × 12 cols
Key finding: <one sentence>
Top 5 by <metric>:
  1. X — value
  2. Y — value
  ...
```

No boilerplate, no "the data shows that", no restating the question.

## Visualization

Describe the chart in one sentence, then provide the code. Do not explain what pandas/matplotlib functions do.

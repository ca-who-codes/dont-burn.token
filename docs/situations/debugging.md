# Situation: Debugging a production issue

Production is throwing errors. You have logs, a stack trace, and a tight window to fix it. Without token discipline, the AI will read log files in full, trace every possible call path, and write verbose explanations while the incident is ongoing.

---

## The expensive default

```
Incident: 500 errors on /api/payments

AI reads: server.log (50,000 lines)              → 180,000 tokens
AI reads: src/controllers/payments.ts            → 3,000 tokens
AI reads: src/services/stripe.ts                 → 2,000 tokens
AI reads: src/middleware/                        → 5,000 tokens
AI responds: "Let me analyze this issue for you.
  First, looking at the logs, I can see that..."
                                                 → 1,500 token preamble

Total before a useful fix: ~190,000 tokens
```

---

## How to run this situation

### Step 1: Compress the logs before the session

```bash
# Raw logs → signal only
cat /var/log/myapp/server.log | python3 ~/dontburn/session/compress.py --type logs

# Or filter to the incident window first
grep "2026-06-22 14:" /var/log/myapp/server.log | \
  python3 ~/dontburn/session/compress.py --type logs
```

**Before:**
```
2026-06-22 14:00:01 DEBUG GET /health 200 2ms
2026-06-22 14:00:01 DEBUG ping received
2026-06-22 14:00:02 DEBUG GET /health 200 1ms
2026-06-22 14:00:03 ERROR Payment processing failed
  at StripeService.charge (stripe.ts:88)
  at PaymentController.create (payments.ts:42)
2026-06-22 14:00:04 WARN Retry 1/3 for order #8821
2026-06-22 14:00:04 DEBUG health check ok
2026-06-22 14:00:05 ERROR Payment processing failed
  at StripeService.charge (stripe.ts:88)
  ...
```

**After (compress.py --type logs):**
```
       [142 debug/health-check lines omitted]
    8  ERROR Payment processing failed
    9    at StripeService.charge (stripe.ts:88)
   10    at PaymentController.create (payments.ts:42)
   11  WARN Retry 1/3 for order #8821
   16  ERROR Payment processing failed
   17    at StripeService.charge (stripe.ts:88)
```

Reduction: 142 noise lines removed. Stack trace preserved.

### Step 2: Start the session lean

```
Read CLAUDE.md, then snapshot/project.md. Then wait.

[paste compressed log excerpt]

The stack trace points to stripe.ts:88. Fix the payment processing failure.
```

### Step 3: The AI reads surgically

With CLAUDE.md in effect and the compressed log as input:

```
AI: [reads src/services/stripe.ts:80-100 only]

    stripe.ts:88 — stripe.charges.create() is called without a try/catch.
    When Stripe returns a card_declined error, it throws a StripeCardError
    which propagates unhandled.

    src/services/stripe.ts:85-92
    - const charge = await stripe.charges.create({
    -   amount: order.total,
    -   currency: 'usd',
    -   source: order.paymentToken,
    - })
    + try {
    +   const charge = await stripe.charges.create({
    +     amount: order.total,
    +     currency: 'usd',
    +     source: order.paymentToken,
    +   })
    + } catch (err) {
    +   if (err.type === 'StripeCardError') throw new PaymentDeclinedError(err.message)
    +   throw err
    + }
```

No preamble. No summary. 6 targeted lines read. Fix applied.

---

## Token comparison

| Approach | Input tokens | Output tokens |
|----------|-------------|--------------|
| Full log + blind exploration | 185,000 | 3,000 |
| Compressed log + snapshot | 3,500 | 800 |
| **Saving** | **98%** | **73%** |

**In dollars (Sonnet 4.6):** $0.60 → $0.02. A 97% cost reduction for a single debugging session.

---

## Tips for incident response

### Pre-compress logs at the source

Add to your deployment setup:
```bash
# In your incident runbook
alias incident-logs="tail -n 500 /var/log/app/server.log | \
  python3 ~/dontburn/session/compress.py --type logs"
```

### Stack trace is enough most of the time

If you have a clean stack trace, don't paste the whole log. The stack trace is already the compressed signal:

```
You: Getting this error on /api/payments:

    Error: Cannot read property 'id' of undefined
      at PaymentController.create (payments.ts:42:18)
      at Layer.handle [as handle_request] (express/router/layer.js:95:5)

    Fix it.
```

The AI has enough. It reads `payments.ts:42` and solves it without reading any log.

### Know your error budget before starting

For a production incident, time > tokens. Don't compress if compression adds 30 seconds and the incident has been live for 2 hours. The savings matter more in non-urgent debugging.

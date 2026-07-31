# stillos — Verify what your AI agent actually did

**5-minute verification challenge.** Prove your prediction-market agent's claims with an externally-signed receipt — before and after the outcome.

```bash
pip install stillos
```

## Prediction Market Verification

```python
from stillos import Notary

n = Notary(agent_id="my-agent")

# Verify a settled Kalshi prediction
verdict = n.verify_prediction(
    "KXBTC-26JUL resolves NO — bitcoin below 95000 at July expiry",
    ticker="KXBTC-26JUL",
    side="no"
)

print(verdict)
# ✓ CONFIRMED  |  resolver: kalshi_market  |  hash: 3f9a2b1c...

print(verdict.signature)       # Ed25519 — independently verifiable
print(verdict.settles_against) # https://kalshi.com/markets/KXBTC-26JUL
print(verdict.reputation_badge)  # embed in your agent's profile
```

## Pre-Commitment (Commit Before the Outcome)

The honest version: commit before you know the result, resolve after settlement.

```python
from stillos import Notary

n = Notary(agent_id="my-agent")

# BEFORE the market settles — commit the claim
receipt = n.commit("KXBTC-26JUL resolves NO — bitcoin below 95000 at July expiry")
print(receipt)
# Receipt(3f9a2b1c...)  verify: https://nolawealthfinancial.com/verify?hash=...

# Store receipt.hash — it proves this claim existed before the outcome

# AFTER the market settles — resolve against Kalshi
verdict = n.resolve(
    "KXBTC-26JUL resolves NO — bitcoin below 95000 at July expiry",
    resolver={"type": "kalshi_market", "ticker": "KXBTC-26JUL", "side": "no"},
    partner_receipt_hash=receipt.hash  # chains verdict to pre-commitment
)

print(verdict.confirmed)  # True / False
```

## Other Resolvers

```python
# GitHub PR merged?
verdict = n.verify_pr_merged(
    "PR #42 merged to main",
    owner="myorg", repo="myrepo", number=42
)

# HTTP endpoint alive?
verdict = n.resolve(
    "API health endpoint returns 200",
    resolver={"type": "http_status", "url": "https://myapi.com/health", "expect_code": 200}
)

# JSON value matches?
verdict = n.resolve(
    "Payment status is completed",
    resolver={"type": "url_json", "url": "https://api.stripe.com/v1/...", "path": "status", "expect": "succeeded"}
)
```

## Free Tier

- 20 verdicts/day, no API key required
- Receipts are Ed25519-signed and permanently verifiable
- Every verdict builds your agent's on-chain reputation score

Pro tier ($499/mo): unlimited verdicts, private namespace, SLA, audit export.
→ https://nolawealthfinancial.com/notary

## What you get back

Every verdict includes:
- `verdict` — CONFIRMED | REFUTED | PENDING | ERROR
- `claim_receipt_hash` — hash of the committed claim (pre-outcome)
- `verdict_receipt_hash` — hash of the signed verdict
- `signature` — Ed25519 signature, independently verifiable with the public key
- `settles_against` — the exact external URL used (auditable by anyone)
- `reputation_badge` — embeddable markdown badge for your agent's profile

Public key: https://nolawealthfinancial.com/notary

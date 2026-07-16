# stillos-notary

Direct tool access to StillOS's signed, x402-paid verification and screening primitives — no separate API docs lookup, no SDK install beyond this package.

## Install (MCP)

```json
{
  "mcpServers": {
    "stillos-notary": {
      "command": "npx",
      "args": ["-y", "stillos-notary", "mcp"]
    }
  }
}
```

## Tools

- **notary_commit** — commit any claim string to a tamper-evident, Ed25519-signed receipt. $0.10 USDC on Base.
- **notary_claim_verdict** — signed verdict on a claim, resolved against a named external ground-truth source. Launch price $0.05 USDC on Base through 2026-10-13.
- **notary_screen_entity** — OFAC SDN sanctions name screen, signed receipt, freshness timestamp. $0.001 USDC on Base.
- **notary_distress_score** — validated corporate distress-foresight score (Altman Z-score from live SEC XBRL). Backtested 71% sensitivity / 100% specificity / ~109-day median lead on real Chapter 11 filings. $0.15 USDC on Base.

## Payment

Every tool call is a real HTTP POST to `https://nolawealthfinancial.com/notary/*`. An unpaid call returns the endpoint's real x402 402 response verbatim — parse the `accepts[]` array, pay, and retry the same tool call with an `x_payment_header` argument containing your `X-PAYMENT` header value.

Every paid response is Ed25519-signed and independently verifiable at `GET /notary/verify?hash=...` — you don't have to trust StillOS's word for it.

Backed by a $10 on-chain correctness bond: any counterparty can dispute a signed verdict and get paid up to $1 if it's proven wrong against its own cited source. See `/notary/dispute`.

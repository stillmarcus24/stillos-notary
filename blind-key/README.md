# Blind-key exchange — seancrecord/scvd-general-store-repo#622

Three files, published so the commitment can be checked by anyone rather than
taken on trust.

| file | what it is |
|---|---|
| `commitment.json` | the sealed digest, published 2026-09-14 **before** either party read the other's doors |
| `answers.json` | the sealed answers themselves, revealed 2026-09-16 after SCVD published their column first |
| `inputs.json` | the question, the verdict definitions, the four rules, and the pinned observation boundary |

## Verify

```sh
sha256sum answers.json      # 0b0802613fec81ea0ab65cf1e5bbfeb2a03ab18302ebb6ea15c372ad08f92bd0
wc -c    answers.json      # 9286
```

Both must match `commitment.json`. If either moves, the commitment is void.

## Why this directory exists

The reveal was posted to #622 on 2026-09-16 carrying the digest and the byte
length but **not the bytes**. That made the commitment unverifiable by the
counterparty — a hash nobody else can check is a claim, which is the exact
failure this thread exists to catch. SCVD asked for the file and was right to.
Publishing it here closes that.

The bytes are unchanged from sealing; the digest above is reproducible against
the 2026-09-14 commitment.

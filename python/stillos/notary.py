"""
stillos.notary — minimal client for the StillOS Notary.

Free tier: 20 verdicts/day, no API key required.
Pro tier:  unlimited, pass api_key= to Notary().

Docs: https://nolawealthfinancial.com/notary
"""
import urllib.request
import urllib.error
import json
from dataclasses import dataclass, field
from typing import Optional, Any

BASE_URL = "https://nolawealthfinancial.com/notary"


def _post(url: str, payload: dict, api_key: Optional[str] = None) -> dict:
    body = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json", "User-Agent": "stillos-sdk/0.1.0"}
    if api_key:
        headers["X-Api-Key"] = api_key
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            err = json.loads(raw)
        except Exception:
            err = {"error": raw}
        raise NotaryError(e.code, err) from e


class NotaryError(Exception):
    def __init__(self, status: int, body: dict):
        self.status = status
        self.body = body
        msg = body.get("error") or body.get("message") or str(body)
        super().__init__(f"HTTP {status}: {msg}")


@dataclass
class Verdict:
    verdict: str                    # "CONFIRMED" | "REFUTED" | "PENDING" | "ERROR"
    outcome: Optional[bool]
    claim_receipt_hash: str
    verdict_receipt_hash: str
    signature: str                  # Ed25519 — independently verifiable
    settles_against: str            # the external source used
    resolver_type: str
    resolver_confidence: float
    reputation_badge: Optional[str] = None
    raw: dict = field(default_factory=dict, repr=False)

    @property
    def confirmed(self) -> bool:
        return self.verdict == "CONFIRMED"

    @property
    def refuted(self) -> bool:
        return self.verdict == "REFUTED"

    def __str__(self) -> str:
        icon = "✓" if self.confirmed else ("✗" if self.refuted else "?")
        return f"{icon} {self.verdict}  |  resolver: {self.resolver_type}  |  hash: {self.claim_receipt_hash[:16]}..."


@dataclass
class Receipt:
    """Returned by Notary.commit() — a pre-commitment receipt before any outcome is known."""
    claim: str
    hash: str
    verify_url: str
    signature: str
    raw: dict = field(default_factory=dict, repr=False)

    def __str__(self) -> str:
        return f"Receipt({self.hash[:16]}...)  verify: {self.verify_url}"


class Notary:
    """
    StillOS Notary client.

    Quick start (free tier):
        from stillos import Notary
        n = Notary()
        verdict = n.verify_prediction("KXBTC-26JUL resolves NO", ticker="KXBTC-26JUL", side="no")
        print(verdict)

    Pre-commitment (commit before outcome, resolve later):
        receipt = n.commit("KXBTC-26JUL resolves NO")
        # ... market settles ...
        verdict = n.resolve(receipt.claim, resolver={"type": "kalshi_market", "ticker": "KXBTC-26JUL", "side": "no"})
    """

    def __init__(
        self,
        agent_id: str = "anon",
        api_key: Optional[str] = None,
        base_url: str = BASE_URL,
    ):
        self.agent_id = agent_id
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    # ── core: resolve a claim against an external source in one call ─────────────────────
    def resolve(self, claim: str, resolver: dict, partner_receipt_hash: Optional[str] = None) -> Verdict:
        """
        Commit a claim and immediately resolve it against an external source.
        The commit timestamp is recorded before the resolution call — tamper-evident.

        resolver examples:
          {"type": "kalshi_market", "ticker": "KXBTC-26JUL", "side": "no"}
          {"type": "github_pr", "owner": "myorg", "repo": "myrepo", "number": 42}
          {"type": "http_status", "url": "https://myapi.com/health", "expect_code": 200}
          {"type": "url_json", "url": "https://api.x.com/status", "path": "status", "expect": "ok"}
        """
        payload: dict[str, Any] = {"agent": self.agent_id, "claim": claim, "resolver": resolver}
        if partner_receipt_hash:
            payload["partner_receipt_hash"] = partner_receipt_hash
        data = _post(f"{self.base_url}/claim-verdict", payload, self.api_key)
        return self._parse_verdict(data)

    # ── prediction market shorthand ───────────────────────────────────────────────────────
    def verify_prediction(self, claim: str, ticker: str, side: str = "yes") -> Verdict:
        """
        Verify a prediction-market claim against Kalshi settlement.

        side="yes"  → claim was that YES wins
        side="no"   → claim was that NO wins

        Example:
            verdict = n.verify_prediction(
                "KXBTC-26JUL resolves NO (bitcoin below 95000 at July expiry)",
                ticker="KXBTC-26JUL",
                side="no"
            )
        """
        return self.resolve(claim, {"type": "kalshi_market", "ticker": ticker, "side": side})

    # ── github shorthand ──────────────────────────────────────────────────────────────────
    def verify_pr_merged(self, claim: str, owner: str, repo: str, number: int) -> Verdict:
        """Verify that a GitHub PR was merged."""
        return self.resolve(claim, {"type": "github_pr", "owner": owner, "repo": repo, "number": number})

    # ── pre-commitment: commit before outcome is known, resolve later ─────────────────────
    def commit(self, claim: str) -> Receipt:
        """
        Commit a claim BEFORE the outcome is known.
        Returns a receipt with a hash you store — then call resolve() later with that hash
        as partner_receipt_hash to chain the pre-commitment to the verdict.

        Note: commit() uses the /score endpoint which is free and keyless.
        For a full pre-commitment receipt with Ed25519 signature, use the Pro tier.
        """
        payload = {"agent": self.agent_id, "claim": claim, "category": "pre_commitment", "model_p": 0.5}
        data = _post(f"{self.base_url}/score", payload, self.api_key)
        receipt_hash = data.get("receipt_hash") or data.get("claim_hash") or ""
        sig = data.get("signature") or data.get("notary_sig") or ""
        verify_url = f"{self.base_url}/verify?hash={receipt_hash}"
        return Receipt(claim=claim, hash=receipt_hash, verify_url=verify_url, signature=sig, raw=data)

    # ── internal ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _parse_verdict(data: dict) -> Verdict:
        # `.get(key, {})` only applies the default when the key is ABSENT --
        # the real API explicitly returns `"verdict_receipt": null` on every
        # free-tier (unsigned) verdict, which is the majority of real traffic,
        # so `.get()` returned None there and every free-tier call crashed.
        # `or {}` covers both "key absent" and "key present but falsy/None".
        v = data.get("verdict") or {}
        vr = data.get("verdict_receipt") or {}
        cr = data.get("claim_receipt") or {}
        rep = data.get("reputation")
        badge = rep.get("embed_markdown") if rep else None
        return Verdict(
            verdict=v.get("verdict", "UNKNOWN"),
            outcome=v.get("outcome"),
            claim_receipt_hash=cr.get("hash", ""),
            verdict_receipt_hash=vr.get("hash", ""),
            signature=vr.get("signature", ""),
            settles_against=v.get("settles_against", ""),
            resolver_type=v.get("resolver_type", ""),
            resolver_confidence=float(v.get("resolver_confidence") or 0),
            reputation_badge=badge,
            raw=data,
        )

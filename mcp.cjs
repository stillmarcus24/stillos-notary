'use strict';
/*
 * MCP stdio server for stillos-notary — direct tool access to StillOS's real,
 * signed, x402-paid verification/screening endpoints. Newline-delimited
 * JSON-RPC 2.0. Zero external deps.
 *
 * Each tool is a thin proxy: it POSTs to the real live endpoint. An unpaid call
 * returns the endpoint's real 402 response verbatim (the accepts[] array with
 * price/network/payTo), so the calling agent can pay and retry with an
 * x_payment_header argument -- no separate documentation lookup required.
 */
const https = require('https');
const http = require('http');
const { URL } = require('url');

const SERVER = { name: 'stillos-notary', version: '1.0.0' };
const PROTOCOL = '2024-11-05';
const NOTARY = process.env.STILLOS_NOTARY || 'https://nolawealthfinancial.com/notary';
const DEFAULT_AGENT = `mcp-client-${Math.random().toString(36).slice(2, 8)}`;

function call(path, body, xPaymentHeader) {
  return new Promise((resolve) => {
    let u; try { u = new URL(NOTARY.replace(/\/+$/, '') + path); } catch { return resolve({ error: 'bad NOTARY base url' }); }
    const lib = u.protocol === 'http:' ? http : https;
    const data = JSON.stringify(body);
    const headers = { 'content-type': 'application/json', 'content-length': Buffer.byteLength(data) };
    if (xPaymentHeader) headers['X-PAYMENT'] = xPaymentHeader;
    const req = lib.request(u, { method: 'POST', headers }, (res) => {
      let b = ''; res.on('data', c => b += c);
      res.on('end', () => {
        try { resolve({ status: res.statusCode, body: JSON.parse(b) }); }
        catch { resolve({ status: res.statusCode, body: b }); }
      });
    });
    req.on('error', (e) => resolve({ error: e.message }));
    req.setTimeout(15000, () => { req.destroy(); resolve({ error: 'timeout' }); });
    req.end(data);
  });
}

// One entry per real paid endpoint this session verified live on notary_service_marcus.cjs.
const ENDPOINTS = {
  notary_commit: {
    path: '/commit',
    description: 'Commit any claim string to a tamper-evident, Ed25519-signed receipt. $0.10 USDC on Base. Backed by a $10 on-chain correctness bond.',
    schema: { agent: { type: 'string' }, claim: { type: 'string', description: 'the claim text to notarize' } },
    required: ['claim'],
  },
  notary_claim_verdict: {
    path: '/claim-verdict',
    description: 'Signed verdict on a claim, resolved against a named external ground-truth source, Ed25519-signed and hash-chained. Launch price $0.05 USDC on Base through 2026-10-13.',
    schema: { agent: { type: 'string' }, claim: { type: 'string' }, resolver: { type: 'string', description: 'named external resolver' } },
    required: ['claim', 'resolver'],
  },
  notary_screen_entity: {
    path: '/screen-entity',
    description: 'OFAC SDN sanctions name screen with signed receipt and source freshness timestamp. $0.001 USDC on Base.',
    schema: { entity: { type: 'string', description: 'legal name to screen against OFAC SDN' } },
    required: ['entity'],
  },
  notary_distress_score: {
    path: '/distress-score',
    description: 'Validated corporate distress-foresight score for a single equity ticker (Altman Z-score from live SEC XBRL, point-in-time, non-financials only). Backtested 71% sensitivity / 100% specificity / ~109-day median lead on real Chapter 11 filings. $0.15 USDC on Base.',
    schema: { agent: { type: 'string' }, ticker: { type: 'string', description: 'equity ticker' } },
    required: ['ticker'],
  },
};

const TOOLS = Object.entries(ENDPOINTS).map(([name, e]) => ({
  name,
  description: e.description,
  inputSchema: {
    type: 'object',
    properties: { ...e.schema, x_payment_header: { type: 'string', description: 'optional X-PAYMENT header value (x402 v1) from a prior 402 response, to complete payment and retry' } },
    required: e.required,
  },
}));

function write(obj) { process.stdout.write(JSON.stringify(obj) + '\n'); }
function reply(id, result) { write({ jsonrpc: '2.0', id, result }); }
function replyError(id, code, message) { write({ jsonrpc: '2.0', id, error: { code, message } }); }

async function handle(msg) {
  const { id, method, params } = msg;
  if (method === 'initialize') return reply(id, { protocolVersion: PROTOCOL, capabilities: { tools: {} }, serverInfo: SERVER });
  if (method === 'notifications/initialized' || method === 'initialized') return;
  if (method === 'tools/list') return reply(id, { tools: TOOLS });
  if (method === 'ping') return reply(id, {});
  if (method === 'tools/call') {
    const name = params && params.name;
    const args = (params && params.arguments) || {};
    const endpoint = ENDPOINTS[name];
    if (!endpoint) return replyError(id, -32601, `unknown tool: ${name}`);
    const { x_payment_header, ...body } = args;
    if (!body.agent) body.agent = DEFAULT_AGENT;
    const result = await call(endpoint.path, body, x_payment_header);
    return reply(id, { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] });
  }
  if (id !== undefined) return replyError(id, -32601, `unknown method: ${method}`);
}

let buf = '';
process.stdin.on('data', (chunk) => {
  buf += chunk;
  let idx;
  while ((idx = buf.indexOf('\n')) >= 0) {
    const line = buf.slice(0, idx); buf = buf.slice(idx + 1);
    if (!line.trim()) continue;
    try { handle(JSON.parse(line)); } catch { /* ignore malformed line */ }
  }
});
process.stdin.resume();

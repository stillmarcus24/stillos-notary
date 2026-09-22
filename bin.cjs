#!/usr/bin/env node
'use strict';
/*
 * stillos-notary CLI / MCP entry.
 *   stillos-notary mcp   -> run as an MCP stdio server (for agents/clients)
 */
const args = process.argv.slice(2);
if (args[0] === 'mcp') { require('./mcp.cjs'); } else {
  console.log('stillos-notary — direct tool access to StillOS signed verification/screening endpoints.\n');
  console.log('  stillos-notary mcp   run as MCP server\n');
  console.log('Tools: notary_commit, notary_claim_verdict, notary_screen_entity, notary_distress_score');
  console.log('Every response is Ed25519-signed and independently verifiable. https://stillosdigitalholdings.com/notary');
  process.exit(0);
}

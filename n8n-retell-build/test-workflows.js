const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

for (const file of ['outbound-campaigns.json', 'suppression-webhooks.json', 'error-handler.json']) {
  const workflow = JSON.parse(fs.readFileSync(path.join(__dirname, file), 'utf8'));
  assert.equal(workflow.active, false, `${file} must import inactive`);
  const names = new Set(workflow.nodes.map(n => n.name));
  assert.equal(names.size, workflow.nodes.length, `${file} has duplicate node names`);
  for (const [source, outputs] of Object.entries(workflow.connections)) {
    assert(names.has(source), `${file}: missing source ${source}`);
    for (const output of outputs.main) for (const edge of output) assert(names.has(edge.node), `${file}: missing target ${edge.node}`);
  }
  for (const n of workflow.nodes.filter(n => n.type === 'n8n-nodes-base.code')) new Function(n.parameters.jsCode);
}

const main = JSON.parse(fs.readFileSync(path.join(__dirname, 'outbound-campaigns.json'), 'utf8'));
const rules = main.nodes.find(n => n.name === 'Campaign Timing Rules').parameters.jsCode;
for (const phrase of ['48 hours', 'day 5', '30 days', '85 days', '150 days', '2 hours', '24 hours', '04-01', '09-15', '03-15']) assert(rules.includes(phrase), phrase);
assert(main.nodes.some(n => n.name === 'Check Shared Suppression'));
assert(main.nodes.some(n => n.name === 'Start Seasonal Call (Retell)'));
console.log('Outbound Retell+n8n package: structure, inactive defaults, code syntax, and timing rules passed');

const retell = JSON.parse(fs.readFileSync(path.join(__dirname, 'Outbound Seasonal Follow-Up - Retell + n8n v0.json'), 'utf8'));
assert.equal(retell.is_published, false);
assert.equal(retell.conversationFlow.is_published, false);
assert.equal(retell.webhook_url, 'https://n8n.sohaib.systems/webhook/outbound-voice-status');
assert.deepEqual(retell.webhook_events, ['call_analyzed']);
const retellIds = new Set(retell.conversationFlow.nodes.map(n => n.id));
for (const n of retell.conversationFlow.nodes) for (const edge of n.edges || []) assert(retellIds.has(edge.destination_node_id));
assert(retell.post_call_analysis_data.some(field => field.name === 'do_not_call'));
console.log('Outbound Retell agent: import structure, DNC analysis, webhook, and conversation edges passed');

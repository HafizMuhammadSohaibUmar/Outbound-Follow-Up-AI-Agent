const fs = require('node:fs');
const path = require('node:path');

const out = __dirname;
const expr = (s) => `={{ ${s} }}`;
const body = (fn) => fn.toString().slice(fn.toString().indexOf('{') + 1, -1).trim();
const node = (name, type, typeVersion, parameters, x, y, extra = {}) => ({
  id: name.toLowerCase().replace(/[^a-z0-9]+/g, '-'), name,
  type: `n8n-nodes-base.${type}`, typeVersion, parameters, position: [x, y], ...extra,
});
const link = (name, index = 0) => ({ node: name, type: 'main', index });

function campaignRules() {
  const source = $input.first().json.source;
  const now = new Date();
  const rules = {
    estimate_followup: 'Run every 6 hours. Select pending estimates first at 48 hours, then once more on day 5. Maximum two SMS attempts.',
    job_reengagement: 'Run daily at 08:00. Select general completed jobs at 30 days, pest-control jobs at 85 days, and HVAC/AC/furnace/heating jobs at 150 days. SMS only.',
    seasonal: 'Run daily at 09:00, but send only on configured launch dates: HVAC 04-01 and 09-15; pest 03-01, 06-01, and 09-01; roofing 03-15. Select customers active in the previous 24 months. Voice via Retell only.',
    noshow_recovery: 'Run every 2 hours. Select missed appointments for SMS at 2 hours and once more at 24 hours. Maximum two attempts.',
  };
  const dates = { '04-01': 'HVAC tune-up', '09-15': 'HVAC tune-up', '03-01': 'pest control service', '06-01': 'pest control service', '09-01': 'pest control service', '03-15': 'roof inspection' };
  const mmdd = `${String(now.getUTCMonth() + 1).padStart(2, '0')}-${String(now.getUTCDate()).padStart(2, '0')}`;
  if (source === 'seasonal' && !dates[mmdd]) return [];
  return [{ json: { source, rule: rules[source], seasonal_service: dates[mmdd] || null, evaluated_at: now.toISOString() } }];
}

function normalizeCandidates() {
  const meta = $('Campaign Timing Rules').first().json;
  const payload = $input.first().json;
  const rows = payload.data?.quotes?.nodes || payload.data?.jobs?.nodes || payload.data?.clients?.nodes || payload.data?.visits?.nodes || payload.data || payload.jobs || payload.estimates || payload.customers || [];
  const list = Array.isArray(rows) ? rows : [];
  const phone = (r) => r.phone || r.phone_number || r.phones?.[0]?.number || r.client?.phones?.[0]?.number || r.customer?.phones?.[0]?.number;
  const name = (r) => r.name || r.customer_name || r.client?.name || r.customer?.name || 'there';
  return list.map((r) => ({ json: {
    business_id: 'REPLACE_WITH_BUSINESS_ID', campaign_type: meta.source,
    phone: phone(r), name: name(r), source_id: r.id,
    service_type: r.title || r.service_type || meta.seasonal_service || 'home service',
    amount: r.total || r.amount || null, rule: meta.rule, fetched_at: meta.evaluated_at,
  }})).filter((i) => /^\+[1-9]\d{7,14}$/.test(String(i.json.phone || '')));
}

function suppressionDecision() {
  const candidate = $('Normalize FSM Candidates').item.json;
  const rows = $input.all().map(i => i.json).filter(r => r.phone_number);
  return [{ json: { ...candidate, suppressed: rows.some(r => r.phone_number === candidate.phone) } }];
}

function composeMessage() {
  const c = $input.first().json;
  const business = 'REPLACE_WITH_BUSINESS_NAME';
  const owner = 'REPLACE_WITH_OWNER_FIRST_NAME';
  const messages = {
    estimate_followup: `Hi ${c.name}, this is ${owner} with ${business}. Just checking in on the ${c.service_type} estimate we sent. Would you like us to help get it scheduled? Reply STOP to opt out.`,
    job_reengagement: `Hi ${c.name}, this is ${owner} with ${business}. We helped with your ${c.service_type} before and wanted to see if you need anything scheduled. Reply STOP to opt out.`,
    noshow_recovery: `Hi ${c.name}, this is ${owner} with ${business}. Sorry we missed you for the appointment. Would you like us to find another time? Reply STOP to opt out.`,
  };
  return [{ json: { ...c, message: messages[c.campaign_type] || '' } }];
}

const schedule = (name, rule, source, x, y) => node(name, 'scheduleTrigger', 1.2, { rule }, x, y, { notes: source });
const main = {
  id: 'OutboundRtN8n20261010', name: 'Outbound Follow-Up - Retell + n8n (inactive until configured)', active: false,
  settings: { executionOrder: 'v1', timezone: 'America/New_York', errorWorkflow: '' }, staticData: null,
  nodes: [
    node('Setup and Cost Notes', 'stickyNote', 1, { width: 700, height: 430, content:
      '## Configure before activation\nCredentials: Jobber OAuth2 or Housecall Pro API, Supabase, Twilio, Retell API, and Slack in the separate error workflow. Replace every REPLACE_WITH_* value. Run schema.sql. Select exactly one FSM provider in Read FSM Records. Keep inactive until consent, quiet hours, caller ID, opt-out, and test numbers are verified.\n\n## Voice vendor quote (2026-10-10)\nAssumption: US low-volume pilot, approximately 1,000 seasonal voice minutes/month, no enterprise commitment or add-ons. Retell selected as the lowest clearly verifiable all-in PAYG configuration: $0.0866/min using $0.055 infrastructure + $0.015 platform voice + $0.0016 GPT-5 nano + $0.015 Retell telephony, plus $0.005 per batch dial. Bland starts at $0.14/min before carrier; Vapi charges hosting plus model, voice, transcriber, and telephony. Re-quote all vendors before renewing the client retainer. Voice and telephony are client-billed.' }, -500, -520),
    schedule('Estimate - Every 6 Hours', { interval: [{ field: 'hours', hoursInterval: 6 }] }, 'estimate_followup', -320, -120),
    schedule('Reengagement - Daily 08:00', { interval: [{ field: 'cronExpression', expression: '0 8 * * *' }] }, 'job_reengagement', -320, 20),
    schedule('Seasonal - Daily 09:00', { interval: [{ field: 'cronExpression', expression: '0 9 * * *' }] }, 'seasonal', -320, 160),
    schedule('No Show - Every 2 Hours', { interval: [{ field: 'hours', hoursInterval: 2 }] }, 'noshow_recovery', -320, 300),
    node('Set Estimate Source', 'set', 3.4, { assignments: { assignments: [{ id: 'source', name: 'source', value: 'estimate_followup', type: 'string' }] }, options: {} }, -80, -120),
    node('Set Reengagement Source', 'set', 3.4, { assignments: { assignments: [{ id: 'source', name: 'source', value: 'job_reengagement', type: 'string' }] }, options: {} }, -80, 20),
    node('Set Seasonal Source', 'set', 3.4, { assignments: { assignments: [{ id: 'source', name: 'source', value: 'seasonal', type: 'string' }] }, options: {} }, -80, 160),
    node('Set No Show Source', 'set', 3.4, { assignments: { assignments: [{ id: 'source', name: 'source', value: 'noshow_recovery', type: 'string' }] }, options: {} }, -80, 300),
    node('Campaign Timing Rules', 'code', 2, { jsCode: body(campaignRules) }, 180, 80),
    node('Read FSM Records', 'httpRequest', 4.2, { method: 'POST', url: 'REPLACE_WITH_FSM_READ_ENDPOINT', authentication: 'genericCredentialType', genericAuthType: 'httpHeaderAuth', sendBody: true, specifyBody: 'json', jsonBody: expr("JSON.stringify({provider:'REPLACE_WITH_JOBBER_OR_HOUSECALLPRO', campaign:$json.source, rule:$json.rule, read_only:true})"), options: { timeout: 15000 } }, 420, 80),
    node('Normalize FSM Candidates', 'code', 2, { mode: 'runOnceForAllItems', jsCode: body(normalizeCandidates) }, 660, 80),
    node('Check Shared Suppression', 'supabase', 1, { resource: 'row', operation: 'getAll', tableId: 'outbound_suppression', returnAll: true, filters: { conditions: [{ keyName: 'phone_number', condition: 'eq', keyValue: expr('$json.phone') }] }, options: {} }, 900, 80, { alwaysOutputData: true }),
    node('Decide Suppression', 'code', 2, { jsCode: body(suppressionDecision) }, 1140, 80),
    node('Allowed to Send?', 'if', 2, { conditions: { options: { typeValidation: 'strict' }, conditions: [{ leftValue: expr('$json.suppressed'), rightValue: false, operator: { type: 'boolean', operation: 'equal' } }] }, options: {} }, 1380, 80),
    node('Campaign Router', 'switch', 3, { mode: 'expression', numberOutputs: 2, output: expr("$json.campaign_type === 'seasonal' ? 1 : 0"), options: {} }, 1620, 80),
    node('Compose Deterministic SMS', 'code', 2, { jsCode: body(composeMessage) }, 1860, -60),
    node('Send SMS (Twilio)', 'twilio', 1, { resource: 'sms', operation: 'send', from: 'REPLACE_WITH_TWILIO_E164', to: expr('$json.phone'), message: expr('$json.message') }, 2100, -60),
    node('Start Seasonal Call (Retell)', 'httpRequest', 4.2, { method: 'POST', url: 'https://api.retellai.com/v2/create-phone-call', authentication: 'genericCredentialType', genericAuthType: 'httpHeaderAuth', sendBody: true, specifyBody: 'json', jsonBody: expr("JSON.stringify({from_number:'REPLACE_WITH_RETELL_E164',to_number:$json.phone,override_agent_id:'REPLACE_WITH_RETELL_AGENT_ID',retell_llm_dynamic_variables:{customer_name:$json.name,service_type:$json.service_type,business_name:'REPLACE_WITH_BUSINESS_NAME'}})"), options: { timeout: 15000 } }, 1860, 220),
    node('Log Campaign Send', 'supabase', 1, { resource: 'row', operation: 'create', tableId: 'outbound_campaign_logs', dataToSend: 'defineBelow', fieldsUi: { fieldValues: [
      ['business_id', expr("$('Decide Suppression').item.json.business_id")], ['campaign_type', expr("$('Decide Suppression').item.json.campaign_type")], ['phone', expr("$('Decide Suppression').item.json.phone")], ['source_id', expr("$('Decide Suppression').item.json.source_id")], ['channel', expr("$('Decide Suppression').item.json.campaign_type === 'seasonal' ? 'voice' : 'sms'")], ['outcome', 'sent'], ['vendor_message_id', expr('$json.sid ?? $json.call_id ?? ""')]
    ].map(([fieldId, fieldValue]) => ({ fieldId, fieldValue })) } }, 2340, 80),
  ],
  connections: {
    'Estimate - Every 6 Hours': { main: [[link('Set Estimate Source')]] }, 'Set Estimate Source': { main: [[link('Campaign Timing Rules')]] },
    'Reengagement - Daily 08:00': { main: [[link('Set Reengagement Source')]] }, 'Set Reengagement Source': { main: [[link('Campaign Timing Rules')]] },
    'Seasonal - Daily 09:00': { main: [[link('Set Seasonal Source')]] }, 'Set Seasonal Source': { main: [[link('Campaign Timing Rules')]] },
    'No Show - Every 2 Hours': { main: [[link('Set No Show Source')]] }, 'Set No Show Source': { main: [[link('Campaign Timing Rules')]] },
    'Campaign Timing Rules': { main: [[link('Read FSM Records')]] }, 'Read FSM Records': { main: [[link('Normalize FSM Candidates')]] },
    'Normalize FSM Candidates': { main: [[link('Check Shared Suppression')]] }, 'Check Shared Suppression': { main: [[link('Decide Suppression')]] },
    'Decide Suppression': { main: [[link('Allowed to Send?')]] }, 'Allowed to Send?': { main: [[link('Campaign Router')], []] },
    'Campaign Router': { main: [[link('Compose Deterministic SMS')], [link('Start Seasonal Call (Retell)')]] },
    'Compose Deterministic SMS': { main: [[link('Send SMS (Twilio)')]] }, 'Send SMS (Twilio)': { main: [[link('Log Campaign Send')]] },
    'Start Seasonal Call (Retell)': { main: [[link('Log Campaign Send')]] },
  },
};

function parseOptOut() {
  const p = $input.first().json.body ?? $input.first().json;
  const text = String(p.Body ?? p.body ?? p.transcript ?? p.call?.transcript ?? '').trim();
  const phone = p.From ?? p.from_number ?? p.call?.to_number;
  const vendorDnc = Boolean(p.dnc || p.do_not_call || p.call_analysis?.custom_analysis_data?.do_not_call || p.call?.call_analysis?.custom_analysis_data?.do_not_call);
  const stop = /^(stop|unsubscribe|cancel|quit|end|opt\s*out)$/i.test(text);
  if (!phone || (!stop && !vendorDnc)) return [];
  return [{ json: { phone_number: phone, reason: vendorDnc ? 'vendor_dnc' : 'STOP', source: p.CallSid ? 'twilio' : 'voice_vendor', raw_event_id: p.CallSid ?? p.call_id ?? p.call?.call_id ?? null } }];
}

const suppression = {
  id: 'OutboundSuppress20261010', name: 'Outbound Follow-Up - STOP and DNC Intake', active: false, settings: { executionOrder: 'v1' }, staticData: null,
  nodes: [
    node('Setup Notes', 'stickyNote', 1, { width: 520, height: 250, content: 'Configure Twilio inbound SMS to /webhook/outbound-sms-reply and Retell call_analyzed webhook to /webhook/outbound-voice-status. Verify vendor signatures at the reverse proxy or a dedicated verification service before production. Both routes update the same suppression table.' }, -300, -300),
    node('Twilio Reply Webhook', 'webhook', 1, { httpMethod: 'POST', path: 'outbound-sms-reply', responseMode: 'onReceived', options: {} }, -200, -60),
    node('Voice Status Webhook', 'webhook', 1, { httpMethod: 'POST', path: 'outbound-voice-status', responseMode: 'onReceived', options: {} }, -200, 100),
    node('Parse STOP or DNC', 'code', 2, { jsCode: body(parseOptOut) }, 60, 20),
    node('Upsert Shared Suppression', 'supabase', 1, { resource: 'row', operation: 'upsert', tableId: 'outbound_suppression', dataToSend: 'defineBelow', fieldsUi: { fieldValues: [['phone_number', expr('$json.phone_number')], ['reason', expr('$json.reason')], ['source', expr('$json.source')], ['raw_event_id', expr('$json.raw_event_id')]].map(([fieldId, fieldValue]) => ({ fieldId, fieldValue })) } }, 320, 20),
  ],
  connections: { 'Twilio Reply Webhook': { main: [[link('Parse STOP or DNC')]] }, 'Voice Status Webhook': { main: [[link('Parse STOP or DNC')]] }, 'Parse STOP or DNC': { main: [[link('Upsert Shared Suppression')]] } },
};

const errors = {
  id: 'OutboundError20261010', name: 'Outbound Follow-Up - Error Handler', active: false, settings: { executionOrder: 'v1' }, staticData: null,
  nodes: [
    node('Error Trigger', 'errorTrigger', 1, {}, 0, 0),
    node('Log Error', 'supabase', 1, { resource: 'row', operation: 'create', tableId: 'outbound_workflow_errors', dataToSend: 'defineBelow', fieldsUi: { fieldValues: [['workflow_name', expr('$json.workflow?.name ?? "unknown"')], ['node_name', expr('$json.execution?.lastNodeExecuted ?? "trigger"')], ['error_message', expr('$json.execution?.error?.message ?? $json.trigger?.error?.message ?? "unknown"')], ['execution_id', expr('$json.execution?.id ?? ""')]].map(([fieldId, fieldValue]) => ({ fieldId, fieldValue })) } }, 240, -80),
    node('Alert Owner', 'slack', 2, { resource: 'message', operation: 'post', channel: 'REPLACE_WITH_SLACK_CHANNEL', text: expr("'Outbound campaign failure in ' + ($json.workflow?.name ?? 'unknown') + ' at ' + ($json.execution?.lastNodeExecuted ?? 'trigger') + ': ' + ($json.execution?.error?.message ?? 'unknown error')") }, 240, 100),
  ],
  connections: { 'Error Trigger': { main: [[link('Log Error'), link('Alert Owner')]] } },
};

for (const [name, workflow] of [['outbound-campaigns.json', main], ['suppression-webhooks.json', suppression], ['error-handler.json', errors]]) {
  fs.writeFileSync(path.join(out, name), JSON.stringify(workflow, null, 2) + '\n');
}

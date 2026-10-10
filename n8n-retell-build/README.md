# Outbound Follow-Up: Retell + n8n

This is the separate low-code implementation of the four campaigns in the custom-coded agent. It does not replace or modify the FastAPI version.

## Files

- `outbound-campaigns.json`: four scheduled campaigns, read-only FSM intake, suppression check before every send, Twilio SMS, Retell seasonal calls, and Supabase logging.
- `suppression-webhooks.json`: Twilio STOP and voice-vendor DNC intake into one shared table.
- `error-handler.json`: Supabase error log plus Slack owner alert.
- `Outbound Seasonal Follow-Up - Retell + n8n v0.json`: inactive Retell conversation-flow agent for seasonal calls.
- `schema.sql`: dedicated Supabase tables.
- `build-workflows.js`: reproducible workflow generator.
- `test-workflows.js`: offline structural and timing-rule validation.

## Campaign Rules

| Campaign | Selection and cadence | Channel |
|---|---|---|
| Estimate Follow-Up | Scheduler runs every 6 hours; contact at 48 hours and day 5, maximum two attempts | Twilio SMS |
| Job Completion Re-Engagement | Daily at 08:00; general jobs at 30 days, pest at 85 days, HVAC at 150 days | Twilio SMS |
| Seasonal | Daily check at 09:00; HVAC `04-01,09-15`, pest `03-01,06-01,09-01`, roofing `03-15`; customers from prior 24 months | Retell voice |
| No-Show Recovery | Scheduler runs every 2 hours; contact at 2 hours and 24 hours, maximum two attempts | Twilio SMS |

## Before Import

1. Run `schema.sql` in the intended Supabase project.
2. Import all three JSON workflows. They intentionally import inactive.
3. Configure Supabase, Twilio, Retell HTTP-header, FSM HTTP-header, and Slack credentials.
4. Replace every `REPLACE_WITH_*` placeholder.
5. Implement `REPLACE_WITH_FSM_READ_ENDPOINT` as a read-only adapter for either Jobber or Housecall Pro. It must return the source records; the next Code node normalizes them.
6. Select `error-handler.json` under each other workflow's **Settings > Error workflow**.
7. Point Twilio inbound SMS to `/webhook/outbound-sms-reply` and Retell `call_analyzed` events to `/webhook/outbound-voice-status`.
8. Verify vendor webhook signatures at ingress before production. Test only with consented internal numbers, then activate the suppression workflow before any campaign workflow.

## Pricing Decision

Build-date assumption: 2026-10-10, US low-volume pilot of about 1,000 seasonal voice minutes per month, no enterprise discounts or add-ons. Retell is selected because its documented comparable configuration is approximately **$0.0866/minute** (`$0.055` infrastructure + `$0.015` platform voice + `$0.0016` GPT-5 nano + `$0.015` Retell telephony), plus `$0.005` per batch dial. Re-quote Retell, Vapi, and Bland before renewing a client retainer or when volume/provider contracts change.

## Validation

```powershell
node build-workflows.js
node test-workflows.js
```

Passing structural tests do not prove credentials, API schemas, consent controls, or deliverability. Keep the workflows inactive until end-to-end sandbox tests pass.

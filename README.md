# LeadPilot AI Outbound Follow-Up Agent

AI-powered outbound follow-up automation for home service businesses. The agent runs four campaign types from one FastAPI service:

| Campaign | Trigger | Channel | Goal |
| --- | --- | --- | --- |
| Estimate Follow-Up | 48 hours after a pending estimate, then day 5 | SMS | Recover unscheduled estimates |
| Job Completion Re-Engagement | 30/85/150 days after a completed job | SMS | Bring previous customers back |
| Seasonal Campaign | HVAC, pest control, and roofing seasonal dates | Voice | Call past customers before busy seasons |
| No-Show Recovery | 2 hours and 24 hours after a missed appointment | SMS | Reschedule without sounding pushy |

## Architecture

```text
APScheduler / Manual Run
  -> CampaignRunner subclass
  -> FSM reader or manual contact input
  -> calling-window + suppression + cycle dedup checks
  -> LiteLLM/Mistral message generation
  -> Twilio SMS, dry-run preview, or Agent 1 outbound voice handoff
  -> Supabase campaign_contacts + campaign_logs

Customer SMS Reply
  -> FastAPI /twilio/sms-reply
  -> STOP suppression, accept, decline, or unclear outcome
  -> campaign contact update + owner alert when converted
```

## Engineering Signals

- Four campaign types share one runner contract while keeping their own timing and attempt rules.
- Suppression, cycle deduplication, and timezone-aware contact windows are applied before outreach.
- SMS campaigns and seasonal voice campaigns use separate channel adapters behind the same campaign log model.
- Seasonal voice reuses the existing Agent 1 media-stream pipeline instead of duplicating voice infrastructure.
- Dry-run execution shows the exact message or voice handoff that would be produced without contacting real customers.

## Related AI Systems

| System | Purpose | Live Demo | Repository |
| --- | --- | --- | --- |
| LeadPilot AI Voice Agent | Inbound phone agent for call qualification, emergency detection, and lead logging. | [Live Demo](https://leadpilotai.sohaib.systems/) | [Repository](https://github.com/HafizMuhammadSohaibUmar/LeadPilotAI) |
| Missed Call Text-Back AI Agent | SMS recovery and qualification after no-answer or busy calls. | [Live Demo](https://missed-call-text-back-ai-agent.sohaib.systems/demo) | [Repository](https://github.com/HafizMuhammadSohaibUmar/Missed-Call-Text-Back-AI-Agent) |
| Outbound Follow-Up AI Agent | Estimate, no-show, re-engagement, and seasonal follow-up campaigns. | [Live Demo](https://outbound-followup-ai-agent.sohaib.systems/demo) | **This repo** |
| AI Auto Review Request Agent | Sentiment-aware post-job review and private feedback routing. | [Live Demo](https://ai-review-agent.sohaib.systems/demo) | [Repository](https://github.com/HafizMuhammadSohaibUmar/AI-Auto-Review-Request-Agent) |
| Web Chat Lead Qualifier Agent | Embeddable RAG chat widget for contractor websites. | [Live Demo](https://web-chat-lead-qualifier-agent.sohaib.systems/demo) | [Repository](https://github.com/HafizMuhammadSohaibUmar/Web-Chat-Lead-Qualifier-Agent) |
| Personal AI Agent | Self-hosted task, planning, and local-calendar assistant with LangGraph tools. | [Live Demo](https://personal-ai-agent.sohaib.systems/) | [Repository](https://github.com/HafizMuhammadSohaibUmar/Personal-AI-Agent) |
| Invoxia AI for ERPNext | Frappe/ERPNext assistant layer for navigation, voice input foundations, and live ERP answers. | [Live Demo](https://invoxia.sohaib.systems/) | [Repository](https://github.com/HafizMuhammadSohaibUmar/InvoxiaAI-ERPNext) |

## Voice Campaign Design

Three campaign types in this service use SMS. The seasonal campaign is different: it can launch outbound voice calls for HVAC, pest control, and roofing outreach.

Instead of adding a separate hosted voice-orchestration provider, the seasonal voice path reuses the existing Agent 1 voice pipeline:

Twilio outbound call -> Twilio Media Streams -> Deepgram STT -> LiteLLM -> ElevenLabs Flash TTS.

`integrations/outbound_call_service.py` checks that the Agent 1 repo is available through `AGENT1_REPO_PATH` and starts outbound Twilio calls that point to `AGENT1_PUBLIC_BASE_URL/voice`. In a standalone deployment, the Agent 1 voice modules can be vendored into this repo, but the default setup avoids duplicating working voice code.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Database/Twilio/dry-run health |
| `GET` | `/demo` | Safe browser demo |
| `POST` | `/demo/run` | Dry-run campaign trigger |
| `POST` | `/campaigns/{type}/run` | Run one campaign now |
| `POST` | `/campaigns/{type}/pause` | Pause a campaign |
| `POST` | `/campaigns/{type}/resume` | Resume a campaign |
| `GET` | `/campaigns/metrics` | Conversion metrics per campaign |
| `POST` | `/voice/outbound` | Redirect handoff to Agent 1 voice webhook |
| `POST` | `/twilio/sms-reply` | Customer reply outcome webhook |

Campaign type values:

```text
estimate_followup
job_reengagement
seasonal
noshow_recovery
```

## Supabase

Run `db/migrations/001_init.sql` in the same Supabase project used by the other agents. The migration creates:

- `campaign_contacts`
- `campaign_logs`
- `campaign_state`
- shared `suppression_list`

The suppression table uses `phone_number` for compatibility with Agent 2, which already owns the shared opt-out list.

## Local Run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn main:app --reload --port 8003
```

Open:

```text
http://localhost:8003/demo
```

## Demo Mode

The browser demo runs in dry-run mode. It produces the SMS text or seasonal voice-call handoff that the campaign runner would create after suppression, deduplication, and campaign rules are applied, without sending real messages or placing calls.

## Admin Protection

Manual campaign control endpoints require:

```text
X-LeadPilot-Key: your_campaign_admin_api_key
```

This protects `/campaigns/{type}/run`, `/pause`, and `/resume` when the app is exposed publicly.

## Reply Outcomes

Set the Twilio messaging webhook to:

```text
https://your-domain.example.com/twilio/sms-reply
```

Customer replies are classified as:

- `STOP` style replies: shared suppression list
- booking/approval replies: converted contact, owner alert
- decline replies: declined contact
- unclear replies: marked for follow-up

## Production Notes

- Calling windows are timezone-aware: Monday-Friday 9am-7pm and Saturday 10am-5pm in `CLIENT_TIMEZONE`.
- Campaign deduplication prevents contacting the same phone twice per campaign cycle.
- STOP suppression is shared with the missed-call agent.
- Jobber and Housecall Pro readers are read-only.
- Seasonal calls use the self-hosted Agent 1 voice pipeline instead of paid voice orchestration.



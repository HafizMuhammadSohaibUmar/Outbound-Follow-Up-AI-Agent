# LeadPilot AI Outbound Follow-Up Agent

AI-powered follow-up campaign automation for home-service businesses.

The agent runs four campaign types from one FastAPI service: estimate follow-up, job-completion re-engagement, seasonal voice outreach, and no-show recovery. It applies suppression, deduplication, timezone-aware contact windows, campaign-specific attempt rules, Twilio delivery, Supabase logging, and dry-run previews for safe testing.

## Live Demo

- Live demo: `https://outbound-followup-ai-agent.sohaib.systems/demo`
- Health check: `https://outbound-followup-ai-agent.sohaib.systems/health`
- Repository: `https://github.com/HafizMuhammadSohaibUmar/Outbound-Follow-Up-AI-Agent`

How to evaluate the demo:

1. Select each campaign type.
2. Change the customer/service context.
3. Run the campaign and inspect the generated preview.
4. Confirm SMS campaigns produce customer message previews.
5. Confirm seasonal campaigns show the outbound voice handoff to the LeadPilot AI Voice Agent pipeline.
6. Review the safe database preview for masked campaign activity.

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

## What This Agent Does

- Finds or accepts eligible campaign contacts.
- Runs campaign-specific timing and attempt rules.
- Applies STOP suppression before outreach.
- Prevents duplicate outreach within a campaign cycle.
- Enforces client-local calling windows.
- Generates personalized SMS through LiteLLM/Mistral.
- Sends Twilio SMS or returns dry-run previews.
- Hands seasonal voice campaigns to the LeadPilot AI Voice Agent pipeline.
- Logs contacts and campaign actions in Supabase.
- Supports pause, resume, manual run, metrics, and reply outcome webhooks.

## Campaign Types

| Campaign | Trigger | Channel | Goal |
| --- | --- | --- | --- |
| Estimate Follow-Up | 48 hours after a pending estimate, then day 5 | SMS | Recover unscheduled estimates |
| Job Completion Re-Engagement | 30 days after completion, 85 days for pest control, 150 days for HVAC | SMS | Bring previous customers back |
| Seasonal Campaign | HVAC, pest control, and roofing seasonal dates | Voice | Reactivate past customers before busy seasons |
| No-Show Recovery | 2 hours and 24 hours after a missed appointment | SMS | Reschedule without sounding pushy |

## Architecture

```text
APScheduler or Manual Trigger
  |
  v
CampaignRunner subclass
  |
  +--> Jobber or Housecall Pro read-only reader
  +--> suppression check
  +--> campaign-cycle deduplication
  +--> timezone calling-window check
  +--> LiteLLM/Mistral personalization
  +--> Twilio SMS, dry-run preview, or outbound voice handoff
  +--> Supabase campaign_contacts + campaign_logs

Customer SMS Reply
  |
  v
/twilio/sms-reply
  |
  +--> STOP suppression
  +--> accept, decline, or unclear outcome
  +--> contact status update
  +--> owner alert when converted
```

## Voice Campaign Design

Most campaigns in this service are SMS-first because the message is short and transactional. Seasonal campaigns can use voice because the campaign is broader reactivation across past customers.

The voice path does not use a paid orchestration layer. It reuses the LeadPilot AI Voice Agent pipeline:

```text
Twilio outbound call
  -> LeadPilot AI Voice Agent /voice
  -> Twilio Media Streams
  -> Deepgram STT
  -> LiteLLM
  -> ElevenLabs or Twilio speech response
```

`integrations/outbound_call_service.py` is the boundary between this campaign service and the voice agent.

## API Surface

| Route | Purpose |
| --- | --- |
| `GET /health` | Database, Twilio, and dry-run health |
| `GET /demo` | Human-facing safe campaign demo |
| `POST /demo/run` | Dry-run campaign trigger |
| `POST /campaigns/{type}/run` | Run one campaign manually |
| `POST /campaigns/{type}/pause` | Pause a campaign |
| `POST /campaigns/{type}/resume` | Resume a campaign |
| `GET /campaigns/metrics` | Conversion metrics per campaign |
| `POST /voice/outbound` | Outbound voice handoff endpoint |
| `POST /twilio/sms-reply` | Customer reply outcome webhook |

## Tech Stack

- FastAPI and Uvicorn
- APScheduler
- Twilio SMS and outbound voice call initiation
- LiteLLM with Mistral
- Supabase PostgREST
- Pydantic Settings
- pytz timezone handling
- Docker and Docker Compose
- Pytest and pytest-asyncio

## Production Features

- Four campaign runners behind one shared contract
- Campaign-level deduplication
- Shared STOP suppression with the missed-call agent
- Timezone-aware contact windows
- Pause and resume API
- Metrics endpoint by campaign type
- Read-only Jobber and Housecall Pro reader boundaries
- Dry-run mode for safe evaluation
- Protected manual controls through `X-LeadPilot-Key`
- Reply outcome processing for accept, decline, unclear, and STOP replies

## Local Setup

```bash
cp .env.example .env
pip install -r requirements.txt
uvicorn main:app --port 8003
```

Open:

```text
http://localhost:8003/demo
```

## Database Setup

Run the migration in Supabase SQL Editor:

```text
db/migrations/001_init.sql
```

It creates:

- `campaign_contacts`
- `campaign_logs`
- `campaign_state`
- shared `suppression_list`

## Important Environment Variables

```env
PUBLIC_BASE_URL=
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=
OWNER_PHONE_NUMBER=
MISTRAL_API_KEY=
SUPABASE_URL=
SUPABASE_KEY=
CLIENT_TIMEZONE=America/New_York
DRY_RUN=true
CAMPAIGN_ADMIN_API_KEY=
AGENT1_PUBLIC_BASE_URL=
```

## Tests

```bash
pytest tests/ -v
```

The tests cover:

- campaign happy paths
- suppression paths
- scheduler registration
- demo behavior
- security and outcome handling

## Deployment

```bash
docker compose up --build -d
```

Run with `DRY_RUN=true` until Twilio credentials, opt-out handling, campaign lists, and owner testing are fully configured.

## Current Demo Limitations

- The browser demo does not send live SMS or place live calls.
- Seasonal voice preview requires the LeadPilot AI Voice Agent to be deployed for real outbound calls.
- Jobber and Housecall Pro readers need real API credentials for automated campaign discovery.

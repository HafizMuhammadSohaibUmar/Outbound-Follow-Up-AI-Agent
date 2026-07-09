# LeadPilot AI Outbound Follow-Up Agent

AI-powered outbound follow-up automation for home service businesses. The agent runs four campaign types from one FastAPI service:

| Campaign | Trigger | Channel | Goal |
| --- | --- | --- | --- |
| Estimate Follow-Up | 48 hours after a pending estimate, then day 5 | SMS | Recover unscheduled estimates |
| Job Completion Re-Engagement | 30/85/150 days after a completed job | SMS | Bring previous customers back |
| Seasonal Campaign | HVAC, pest control, and roofing seasonal dates | Voice | Call past customers before busy seasons |
| No-Show Recovery | 2 hours and 24 hours after a missed appointment | SMS | Reschedule without sounding pushy |

## Related Agents

| Agent | Name | Status |
| --- | --- | --- |
| 1 | LeadPilot AI Voice Agent | Live voice intake and qualification |
| 2 | LeadPilot AI Missed Call Text-Back Agent | Missed-call SMS recovery |
| 3 | LeadPilot AI Outbound Follow-Up Agent | This repo |
| 4 | LeadPilot AI Review Request Agent | Review request automation |
| 5 | Customer Reactivation Agent | Planned |

## Why Vapi And Bland AI Are Skipped

This project intentionally avoids paid hosted voice-orchestration tools. For a self-funded demo, Vapi and Bland AI add recurring per-minute or plan-based costs that are not needed to prove the engineering. Seasonal voice calls instead reuse the same self-hosted pipeline from Agent 1:

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

## Safe Demo Mode

Use this for public demos:

```env
DRY_RUN=true
DEMO_MODE_ENABLED=true
```

Dry-run mode generates SMS and voice-call previews without sending real Twilio messages or placing real calls. This is the recommended setting for Twilio trial accounts and recruiter testing.

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

## Deployment

On the DigitalOcean droplet:

```bash
cd /opt
git clone https://github.com/HafizMuhammadSohaibUmar/AI-Outbound-Follow-Up-Agent.git outbound-followup-agent
cd outbound-followup-agent
cp .env.example .env
nano .env
docker compose up --build -d
curl http://localhost:8003/health
```

Caddy example:

```caddyfile
outbound-followup-agent.sohaib.systems {
    reverse_proxy 127.0.0.1:8003
}
```

Then:

```bash
caddy validate --config /etc/caddy/Caddyfile
systemctl reload caddy
```

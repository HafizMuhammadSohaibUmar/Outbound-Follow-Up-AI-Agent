# Decisions

## 1. One Service, Four Campaign Runners

The agent uses one FastAPI service with one `CampaignRunner` base class and four subclasses. This keeps shared production rules in one place: suppression checks, calling-window enforcement, deduplication, message logging, and dry-run behavior.

## 2. SMS For Tactical Follow-Up, Voice For Seasonal Campaigns

Estimate follow-up, job re-engagement, and no-show recovery are SMS-first because they are short, direct, and low-friction. Seasonal campaigns use outbound voice because the goal is broader reactivation across many past customers, where a human-sounding reminder can be more effective.

## 3. No Vapi Or Bland AI

The voice path does not use Vapi or Bland AI. For this build, their paid hosted voice orchestration is unnecessary. Agent 1 already proves the important engineering: Twilio Media Streams, Deepgram STT, LiteLLM reasoning, and ElevenLabs Flash TTS.

`outbound_call_service.py` therefore acts as the boundary between this campaign service and the existing Agent 1 voice stack. It creates the Twilio outbound call and points Twilio at `AGENT1_PUBLIC_BASE_URL/voice`, where Agent 1 creates the call session and opens the media stream. This keeps Agent 3 focused on campaign selection, timing, deduplication, suppression, and logging.

## 4. Same Supabase, Shared Suppression

The migration is designed for the same Supabase project as the other agents. Suppression uses Agent 2's `suppression_list.phone_number` shape so a customer who opts out from missed-call texts is also protected from follow-up campaigns.

## 5. Dry-Run First

`DRY_RUN=true` is the default. In dry-run mode, the system generates the SMS or call preview and writes logs without sending real Twilio messages or placing calls. This supports safe demos and avoids accidental outreach during development.

## 6. Calling Windows

Campaigns enforce client-local calling windows: Monday-Friday 9am-7pm and Saturday 10am-5pm. The browser demo bypasses the calling-window check only for manual demo runs, so public testers can evaluate the workflow at any time.

## 7. Read-Only FSM Integrations

Jobber and Housecall Pro integrations are readers only. This reduces risk and matches the campaign use case: the agent needs to find eligible estimates, completed jobs, and previous customers; it does not need write access to the FSM.

## 8. Metrics

`GET /campaigns/metrics` groups recent logs by campaign type and reports contacts, conversions, and conversion rate. The schema leaves room for later accepted/declined webhook updates without changing the campaign runner contract.

## 9. Protected Manual Controls

Manual run, pause, and resume endpoints require `X-LeadPilot-Key`. The browser demo remains dry-run only; production campaign controls are not left open on the public internet.

## 10. Reply Outcomes

The Twilio SMS reply webhook classifies opt-out, accept, decline, and unclear replies. Accept replies update the latest matching campaign contact to `converted` and notify the owner. Declines stop that campaign contact. STOP replies go into the shared suppression list.

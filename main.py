"""LeadPilot AI Outbound Follow-Up Agent."""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from campaigns.estimate_followup import EstimateFollowUp
from campaigns.job_reengagement import JobCompletionReEngagement
from campaigns.noshow_recovery import NoShowRecovery
from campaigns.seasonal import SeasonalCampaign
from config import get_settings
from handlers_demo import demo_page, demo_run
from integrations.supabase_client import supabase_client
from integrations.twilio_sms_client import twilio_sms_client
from logging_utils import log_event, setup_logging
from models.campaign import CampaignType
from scheduler import start_scheduler, stop_scheduler
from security import require_admin_key, validate_twilio_form
from services.outcome import handle_customer_reply

logger = logging.getLogger("main")

RUNNERS = {
    CampaignType.ESTIMATE_FOLLOWUP.value: EstimateFollowUp,
    CampaignType.JOB_REENGAGEMENT.value: JobCompletionReEngagement,
    CampaignType.SEASONAL.value: SeasonalCampaign,
    CampaignType.NOSHOW_RECOVERY.value: NoShowRecovery,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    start_scheduler()
    log_event(logger, "Outbound follow-up agent starting", action="startup")
    yield
    stop_scheduler()
    log_event(logger, "Outbound follow-up agent stopping", action="shutdown")


app = FastAPI(title="LeadPilot AI Outbound Follow-Up Agent", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")


@app.get("/")
async def root():
    return {"service": "LeadPilot AI Outbound Follow-Up Agent", "status": "ok", "health": "/health"}


@app.get("/demo", response_class=HTMLResponse)
async def browser_demo():
    return await demo_page()


@app.post("/demo/run")
async def browser_demo_run(request: Request):
    return await demo_run(request)


@app.get("/demo/snapshot")
async def demo_snapshot():
    if not get_settings().demo_mode_enabled:
        return {"enabled": False}
    return await supabase_client.demo_snapshot()


@app.post("/campaigns/{campaign_type}/run", dependencies=[Depends(require_admin_key)])
async def run_campaign(campaign_type: CampaignType):
    runner = RUNNERS[campaign_type.value]()
    return (await runner.run()).model_dump(mode="json")


@app.post("/campaigns/{campaign_type}/pause", dependencies=[Depends(require_admin_key)])
async def pause_campaign(campaign_type: CampaignType):
    await supabase_client.set_campaign_paused(campaign_type, True)
    return {"status": "paused", "campaign_type": campaign_type.value}


@app.post("/campaigns/{campaign_type}/resume", dependencies=[Depends(require_admin_key)])
async def resume_campaign(campaign_type: CampaignType):
    await supabase_client.set_campaign_paused(campaign_type, False)
    return {"status": "running", "campaign_type": campaign_type.value}


@app.get("/campaigns/metrics")
async def campaign_metrics():
    return await supabase_client.metrics()


@app.get("/health")
async def health():
    db = await supabase_client.health_check()
    twilio = await twilio_sms_client.health_check()
    return {
        "status": "healthy" if db.get("ok") and twilio.get("ok") else "degraded",
        "business_id": get_settings().business_id,
        "database": db,
        "twilio": twilio,
        "dry_run": get_settings().dry_run,
    }


@app.post("/voice/outbound")
async def outbound_voice_twiml():
    settings = get_settings()
    return Response(
        content=(
            '<?xml version="1.0" encoding="UTF-8"?><Response>'
            f'<Redirect method="POST">{settings.agent1_public_base_url.rstrip("/")}/voice</Redirect>'
            "</Response>"
        ),
        media_type="application/xml",
    )


@app.post("/voice/outbound/status")
async def outbound_voice_status(form: dict = Depends(validate_twilio_form)):
    if form.get("CallStatus") == "completed" and form.get("To"):
        await supabase_client.log_voice_status(form.get("To"), form.get("CallSid", ""), "voice_completed")
    return {"status": "ok", "call_sid": form.get("CallSid"), "call_status": form.get("CallStatus")}


@app.post("/twilio/sms-reply")
async def sms_reply(form: dict = Depends(validate_twilio_form)):
    result = await handle_customer_reply(form.get("From", ""), form.get("Body", ""), form.get("MessageSid", ""))
    return Response(
        content="<Response/>",
        media_type="application/xml",
        headers={"X-LeadPilot-Status": result["status"]},
    )


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run("main:app", host=settings.host, port=settings.port)

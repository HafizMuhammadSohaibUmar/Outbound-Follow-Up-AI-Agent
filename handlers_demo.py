"""Safe browser demo for outbound follow-up campaigns."""
from uuid import uuid4

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse

from campaigns.estimate_followup import EstimateFollowUp
from campaigns.job_reengagement import JobCompletionReEngagement
from campaigns.noshow_recovery import NoShowRecovery
from campaigns.seasonal import SeasonalCampaign
from config import get_settings
from integrations.twilio_sms_client import twilio_sms_client
from models.campaign import CampaignContact, CampaignType


RUNNERS = {
    CampaignType.ESTIMATE_FOLLOWUP.value: EstimateFollowUp,
    CampaignType.JOB_REENGAGEMENT.value: JobCompletionReEngagement,
    CampaignType.SEASONAL.value: SeasonalCampaign,
    CampaignType.NOSHOW_RECOVERY.value: NoShowRecovery,
}


HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>LeadPilot AI Outbound Follow-Up Agent</title>
  <style>
    :root { color-scheme: dark; font-family: Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif; --gold:#C49A1A; --teal:#4FB39F; --cream:#F5F0E4; --muted:#9A9080; --card:#18160E; --line:rgba(255,255,255,0.08); }
    body { margin: 0; background: radial-gradient(circle at top left, rgba(47,143,126,0.16), transparent 34%), #0A0908; color: var(--cream); }
    header { background: rgba(17,16,9,0.92); border-bottom: 1px solid var(--line); padding: 38px 7vw; }
    .pill { display:inline-block; background:rgba(79,179,159,0.12); color:var(--teal); border:1px solid rgba(79,179,159,0.28); padding:8px 14px; border-radius:999px; font-weight:800; }
    h1 { font-size: clamp(34px, 4vw, 58px); margin: 12px 0; letter-spacing:0; }
    p { color:var(--muted); font-size: 18px; line-height:1.65; }
    main { display:grid; grid-template-columns: minmax(0, 1fr) minmax(0, .95fr); gap:28px; padding:36px 7vw; }
    section { background:linear-gradient(180deg, rgba(255,255,255,0.035), rgba(255,255,255,0.015)), var(--card); border:1px solid var(--line); border-radius:18px; padding:28px; }
    label { display:block; font-weight:800; margin:16px 0 8px; font-size:18px; }
    input, select, textarea { width:100%; box-sizing:border-box; border:1px solid var(--line); border-radius:8px; padding:14px 16px; font-size:18px; background:#0f0e09; color:var(--cream); }
    textarea { min-height:120px; resize:vertical; }
    button { margin-top:18px; background:var(--teal); color:#0A0908; border:0; border-radius:7px; padding:14px 20px; font-weight:800; font-size:17px; cursor:pointer; }
    pre { background:#0f172a; color:#f8fafc; border-radius:8px; padding:22px; white-space:pre-wrap; overflow:auto; font-size:15px; }
    .card { border:1px solid var(--line); border-radius:12px; padding:18px; margin-top:14px; background:#111009; }
    .tag { display:inline-block; background:rgba(79,179,159,0.12); color:var(--teal); border:1px solid rgba(79,179,159,0.28); border-radius:999px; padding:6px 12px; font-weight:800; }
    .explain { margin-top: 14px; padding: 14px; border: 1px solid rgba(196,154,26,0.22); border-left: 3px solid var(--gold); border-radius: 10px; background: rgba(196,154,26,0.08); color: var(--muted); font-size: 14px; }
    @media (max-width: 900px) { main { grid-template-columns: 1fr; padding:24px; } header { padding:30px 24px; } }
  </style>
</head>
<body>
  <header>
    <span class="pill">Demo mode</span>
    <h1>LeadPilot AI Outbound Follow-Up Agent</h1>
    <p>Run estimate, re-engagement, seasonal voice, and no-show recovery campaigns without sending real messages.</p>
    <div class="explain">The demo forces dry-run execution. It shows the message or voice-call handoff that would be produced after suppression, deduplication, and campaign rules are applied.</div>
  </header>
  <main>
    <section>
      <h2>Campaign Trigger</h2>
      <form id="demo-form">
        <label>Campaign type</label>
        <select name="campaign_type" id="campaign">
          <option value="estimate_followup">Estimate follow-up</option>
          <option value="job_reengagement">Job completion re-engagement</option>
          <option value="seasonal">Seasonal voice campaign</option>
          <option value="noshow_recovery">No-show recovery</option>
        </select>
        <label>Customer name</label>
        <input name="name" value="Jane Doe">
        <label>Customer phone</label>
        <input id="phone" name="phone" value="+15551234567">
        <label>Service context</label>
        <textarea name="service_context">Pending AC repair estimate for $740, sent 48 hours ago.</textarea>
        <button type="submit">Run Campaign</button>
        <span id="status"></span>
      </form>
    </section>
    <section>
      <h2>Agent Output</h2>
      <pre id="result">Choose a campaign and run the agent.</pre>
      <div id="cards"></div>
    </section>
  </main>
  <script>
    const result = document.getElementById("result");
    const cards = document.getElementById("cards");
    const status = document.getElementById("status");
    function nextPhone() {
      return "+1555" + String(Math.floor(1000000 + Math.random() * 9000000));
    }
    document.getElementById("phone").value = nextPhone();
    document.getElementById("campaign").addEventListener("change", (event) => {
      const context = document.querySelector("textarea[name='service_context']");
      const value = event.target.value;
      if (value === "estimate_followup") context.value = "Pending AC repair estimate for $740, sent 48 hours ago.";
      if (value === "job_reengagement") context.value = "Completed drain cleaning 30 days ago; customer may need preventive maintenance.";
      if (value === "seasonal") context.value = "Past HVAC customer from the last 24 months; pre-summer tune-up campaign.";
      if (value === "noshow_recovery") context.value = "Missed appointment two hours ago for plumbing inspection.";
      document.getElementById("phone").value = nextPhone();
    });
    document.getElementById("demo-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      status.textContent = "Running...";
      cards.innerHTML = "";
      const data = Object.fromEntries(new FormData(event.target).entries());
      const response = await fetch("/demo/run", { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(data) });
      const payload = await response.json();
      result.textContent = JSON.stringify(payload, null, 2);
      (payload.previews || []).forEach((preview) => {
        const div = document.createElement("div");
        div.className = "card";
        div.innerHTML = `<span class="tag">${preview.label}</span><h3>${preview.to}</h3><p>${preview.body}</p>`;
        cards.appendChild(div);
      });
      status.textContent = "Done";
    });
  </script>
</body>
</html>
"""


async def demo_page() -> HTMLResponse:
    if not get_settings().demo_mode_enabled:
        raise HTTPException(status_code=404, detail="Demo disabled")
    return HTMLResponse(HTML)


async def demo_run(request: Request) -> dict:
    settings = get_settings()
    if not settings.demo_mode_enabled:
        raise HTTPException(status_code=404, detail="Demo disabled")
    if not settings.dry_run:
        raise HTTPException(status_code=403, detail="Browser demo requires DRY_RUN=true")
    payload = await request.json()
    twilio_sms_client.dry_run_outbox.clear()
    campaign_type = CampaignType(payload["campaign_type"])
    contact = CampaignContact(
        id=uuid4(),
        phone=payload["phone"],
        name=payload["name"],
        business_id=settings.business_id,
        campaign_type=campaign_type,
        custom_data={"service_type": payload.get("service_context", "service")},
    )
    runner = RUNNERS[campaign_type.value]()
    result = await runner.run([contact], force_run=True)
    action = "Outbound voice call preview" if campaign_type == CampaignType.SEASONAL else "SMS preview"
    outbox = list(twilio_sms_client.dry_run_outbox)
    return {
        "demo_mode": True,
        "dry_run": settings.dry_run,
        "result": result.model_dump(mode="json"),
        "previews": [
            {
                "label": action,
                "to": outbox[-1]["to"] if outbox else contact.phone,
                "body": "Voice call will use Agent 1 media-stream pipeline."
                if campaign_type == CampaignType.SEASONAL
                else (outbox[-1]["body"] if outbox else "No SMS generated."),
            }
        ],
    }

"""APScheduler campaign schedules."""
try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
except ImportError:  # pragma: no cover - production installs APScheduler
    class _Job:
        def __init__(self, job_id: str) -> None:
            self.id = job_id

    class AsyncIOScheduler:
        def __init__(self, timezone: str = "UTC") -> None:
            self.timezone = timezone
            self.running = False
            self._jobs: list[_Job] = []

        def add_job(self, _func, _trigger: str, id: str, **_kwargs) -> None:
            if id not in {job.id for job in self._jobs}:
                self._jobs.append(_Job(id))

        def start(self) -> None:
            self.running = True

        def shutdown(self, wait: bool = False) -> None:
            self.running = False

        def get_jobs(self) -> list[_Job]:
            return list(self._jobs)

from campaigns.estimate_followup import EstimateFollowUp
from campaigns.job_reengagement import JobCompletionReEngagement
from campaigns.noshow_recovery import NoShowRecovery
from campaigns.seasonal import SeasonalCampaign

scheduler = AsyncIOScheduler(timezone="UTC")


def start_scheduler() -> None:
    if scheduler.running:
        return
    scheduler.add_job(EstimateFollowUp().run, "interval", hours=6, id="estimate_followup_check")
    scheduler.add_job(JobCompletionReEngagement().run, "cron", hour=8, minute=0, id="job_reengagement_check")
    scheduler.add_job(SeasonalCampaign().run, "cron", hour=9, minute=0, id="seasonal_campaign_launch")
    scheduler.add_job(NoShowRecovery().run, "interval", hours=2, id="noshows_check")
    scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)

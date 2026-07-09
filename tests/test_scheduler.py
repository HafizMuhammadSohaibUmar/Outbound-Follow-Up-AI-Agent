"""Scheduler tests."""
from scheduler import scheduler, start_scheduler, stop_scheduler


def test_scheduler_registers_required_jobs():
    start_scheduler()
    job_ids = {job.id for job in scheduler.get_jobs()}
    stop_scheduler()

    assert {"estimate_followup_check", "job_reengagement_check", "seasonal_campaign_launch", "noshows_check"} <= job_ids

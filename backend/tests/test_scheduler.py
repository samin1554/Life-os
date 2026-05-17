"""Tests for the scheduler module."""
import pytest
from unittest.mock import patch

pytestmark = pytest.mark.filterwarnings("ignore::UserWarning")


@pytest.fixture(scope="module", autouse=True)
def _start_once():
    from core.scheduler import scheduler, start_scheduler, stop_scheduler

    start_scheduler()
    yield
    stop_scheduler()


def test_scheduler_registers_jobs():
    from core.scheduler import scheduler

    jobs = scheduler.get_jobs()
    job_ids = [j.id for j in jobs]

    assert "pattern_learning_nightly" in job_ids
    assert "weekly_review_sunday" in job_ids


def test_scheduler_pattern_learning_trigger():
    from core.scheduler import scheduler

    job = scheduler.get_job("pattern_learning_nightly")
    assert job is not None
    assert hasattr(job.trigger, "fields")


def test_scheduler_weekly_review_trigger():
    from core.scheduler import scheduler

    job = scheduler.get_job("weekly_review_sunday")
    assert job is not None

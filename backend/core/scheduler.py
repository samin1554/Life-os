"""APScheduler setup — nightly pattern learning + weekly review."""
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from core.database import _get_session_maker
from models import User
from services.notifications import create_notification

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def _pattern_learning_job():
    """Run pattern learning for all users. Triggered nightly at 02:00."""
    from agents.pattern_learning import run_pattern_learning

    logger.info("Pattern learning job started at %s", datetime.now(timezone.utc))

    async with _get_session_maker()() as db:
        result = await db.execute(select(User.id))
        user_ids = [str(row[0]) for row in result.all()]

    for uid in user_ids:
        try:
            async with _get_session_maker()() as db:
                output = await run_pattern_learning(uid, db)
                logger.info(
                    "Pattern learning for %s: %d insights, streak=%d",
                    uid, len(output["insights"]), output["streak"],
                )
                from uuid import UUID
                await create_notification(
                    db,
                    user_id=UUID(uid),
                    notification_type="pattern_insight",
                    title="New patterns discovered",
                    message=f"Found {len(output['insights'])} new insights about your behaviour. Check-in streak: {output['streak']} days.",
                    link="/insights",
                )
        except Exception:
            logger.exception("Pattern learning failed for user %s", uid)

    logger.info("Pattern learning job completed for %d users", len(user_ids))


async def _manager_scan_job():
    """Scan pending tasks and auto-assign to agents. Every 30 minutes."""
    from agents.manager import scan_and_assign

    logger.info("Manager scan started at %s", datetime.now(timezone.utc))

    async with _get_session_maker()() as db:
        result = await db.execute(
            select(User.id).where(User.onboarding_done == True)
        )
        user_ids = [str(row[0]) for row in result.all()]

    total_assigned = 0
    for uid in user_ids:
        try:
            async with _get_session_maker()() as db:
                assigned = await scan_and_assign(uid, db)
                total_assigned += len(assigned)
                if assigned:
                    logger.info("Manager assigned %d tasks for user %s", len(assigned), uid)
        except Exception:
            logger.exception("Manager scan failed for user %s", uid)

    logger.info("Manager scan completed: %d tasks assigned across %d users", total_assigned, len(user_ids))


async def _weekly_review_job():
    """Generate weekly reviews for all users. Triggered Sunday at 20:00."""
    from agents.weekly_review import run_weekly_review

    logger.info("Weekly review job started at %s", datetime.now(timezone.utc))

    async with _get_session_maker()() as db:
        result = await db.execute(
            select(User.id).where(User.onboarding_done == True)
        )
        user_ids = [str(row[0]) for row in result.all()]

    for uid in user_ids:
        try:
            async with _get_session_maker()() as db:
                output = await run_weekly_review(uid, db)
                logger.info(
                    "Weekly review for %s: %d tasks completed",
                    uid, output["stats"]["tasks_completed"],
                )
                from uuid import UUID
                await create_notification(
                    db,
                    user_id=UUID(uid),
                    notification_type="weekly_review_ready",
                    title="Weekly review ready",
                    message=f"Your week in review: {output['stats']['tasks_completed']} tasks completed. {output['stats']['checkins']} check-ins logged.",
                    link="/weekly-review",
                )
        except Exception:
            logger.exception("Weekly review failed for user %s", uid)

    logger.info("Weekly review job completed for %d users", len(user_ids))


def start_scheduler():
    """Register jobs and start the scheduler."""
    if scheduler.running:
        return

    scheduler.add_job(
        _pattern_learning_job,
        trigger=CronTrigger(hour=2, minute=0),
        id="pattern_learning_nightly",
        replace_existing=True,
    )

    scheduler.add_job(
        _manager_scan_job,
        trigger=CronTrigger(minute="*/30"),
        id="manager_agent_scan",
        replace_existing=True,
    )

    scheduler.add_job(
        _weekly_review_job,
        trigger=CronTrigger(day_of_week="sun", hour=20, minute=0),
        id="weekly_review_sunday",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler started with %d jobs", len(scheduler.get_jobs()))


def stop_scheduler():
    """Shut down the scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")

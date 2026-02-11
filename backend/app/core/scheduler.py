"""Task scheduler for periodic jobs."""

import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from app.core.database import get_session
from app.services.program_sync_service import ProgramSyncService

logger = logging.getLogger(__name__)

scheduler: AsyncIOScheduler | None = None


def init_scheduler():
    """Initialize the scheduler."""
    global scheduler
    if scheduler is None:
        scheduler = AsyncIOScheduler(timezone=pytz.timezone('Asia/Shanghai'))
        _register_jobs()
    return scheduler


def _register_jobs():
    """Register scheduled jobs."""
    if scheduler is None:
        return
    
    async def sync_program_info():
        """Scheduled task to sync Program Info from Google Sheets to database."""
        logger.info("Starting scheduled Program Info sync...")
        try:
            sync_service = ProgramSyncService()
            async with get_session() as db:
                result = await sync_service.sync_from_sheets(db)
                logger.info(
                    f"Scheduled sync completed: {result.created} created, "
                    f"{result.updated} updated, {result.total} total"
                )
        except Exception as e:
            logger.error(f"Scheduled sync failed: {str(e)}", exc_info=True)
    
    # Register three scheduled jobs
    scheduler.add_job(
        sync_program_info,
        CronTrigger(hour=9, minute=0, timezone='Asia/Shanghai'),
        id='sync_program_info_morning',
        name='Sync Program Info - Morning (9:00 Beijing)'
    )
    scheduler.add_job(
        sync_program_info,
        CronTrigger(hour=12, minute=0, timezone='Asia/Shanghai'),
        id='sync_program_info_noon',
        name='Sync Program Info - Noon (12:00 Beijing)'
    )
    scheduler.add_job(
        sync_program_info,
        CronTrigger(hour=18, minute=0, timezone='Asia/Shanghai'),
        id='sync_program_info_evening',
        name='Sync Program Info - Evening (18:00 Beijing)'
    )


async def start_scheduler():
    """Start the scheduler."""
    if scheduler is None:
        init_scheduler()
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started")


async def shutdown_scheduler():
    """Shutdown the scheduler."""
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("Scheduler shut down")


import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.services.reminders import schedule_sleep_reminders

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = None

def get_scheduler() -> AsyncIOScheduler:
    """Get the global scheduler instance."""
    global scheduler
    if scheduler is None:
        scheduler = AsyncIOScheduler()
    return scheduler

def start_scheduler():
    """Start the scheduler and add sleep reminder jobs."""
    global scheduler
    if scheduler is None:
        scheduler = AsyncIOScheduler()
    
    # Schedule sleep reminders
    schedule_sleep_reminders(scheduler)
    
    scheduler.start()
    logger.info("Scheduler started successfully")

def stop_scheduler():
    """Stop the scheduler."""
    global scheduler
    if scheduler:
        scheduler.shutdown()
        scheduler = None
        logger.info("Scheduler stopped")

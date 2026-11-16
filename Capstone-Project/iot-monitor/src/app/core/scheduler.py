"""Background loop: runs due scheduled reports and deletes expired ones.

Several server workers can each run this loop; run_due_reports "claims" every schedule with an
atomic UPDATE, so a report is still generated only once.
"""
import asyncio
import logging

from app.services import report_service

logger = logging.getLogger(__name__)


async def scheduler_loop(session_factory, interval_seconds: int) -> None:
    logger.info("Scheduler started (every %ss)", interval_seconds)
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            await asyncio.to_thread(report_service.tick, session_factory)  # keep the event loop free
        except Exception:  # a failing tick must never stop the loop
            logger.exception("Scheduler tick failed")

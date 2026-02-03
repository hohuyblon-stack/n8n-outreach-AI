"""
Agent Scheduler - Built-in scheduler to replace n8n
Runs automated tasks on schedule without external dependencies
"""
import asyncio
import signal
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Callable
from enum import Enum
import json
from pathlib import Path

from loguru import logger

from src.agent import LeadGenerationAgent
from src.agent.lead_agent import AgentConfig, AgentMode


class ScheduleType(Enum):
    """Types of schedules"""
    INTERVAL = "interval"      # Run every X minutes/hours
    DAILY = "daily"            # Run at specific time daily
    CRON = "cron"              # Cron-like expression
    ONCE = "once"              # Run once at specific time


@dataclass
class ScheduleConfig:
    """Configuration for scheduled tasks"""
    # Lead Search Schedule
    search_enabled: bool = True
    search_interval_hours: int = 24  # Search every 24 hours
    search_time: str = "09:00"       # Or at specific time (HH:MM)

    # Follow-up Schedule
    followup_enabled: bool = True
    followup_interval_hours: int = 8  # Check follow-ups every 8 hours

    # Email Sending Schedule
    email_enabled: bool = True
    email_batch_size: int = 20       # Max emails per batch
    email_interval_minutes: int = 30  # Send batch every 30 min

    # Notification Settings
    notify_on_hot_lead: bool = True
    notify_on_reply: bool = True
    notify_daily_summary: bool = True
    summary_time: str = "18:00"      # Daily summary at 6 PM

    # Targets
    default_keywords: List[str] = field(default_factory=lambda: ["spa", "cafe"])
    default_locations: List[str] = field(default_factory=lambda: ["TP.HCM"])
    max_leads_per_search: int = 30


@dataclass
class ScheduledJob:
    """A scheduled job"""
    name: str
    func: Callable
    schedule_type: ScheduleType
    interval_seconds: Optional[int] = None
    run_at: Optional[str] = None  # HH:MM format
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    enabled: bool = True

    def should_run(self) -> bool:
        """Check if job should run now"""
        if not self.enabled:
            return False

        now = datetime.now()

        if self.schedule_type == ScheduleType.INTERVAL:
            if self.last_run is None:
                return True
            return (now - self.last_run).total_seconds() >= self.interval_seconds

        elif self.schedule_type == ScheduleType.DAILY:
            if self.run_at:
                target_time = datetime.strptime(self.run_at, "%H:%M").time()
                if now.time() >= target_time:
                    if self.last_run is None or self.last_run.date() < now.date():
                        return True
            return False

        return False


class AgentScheduler:
    """
    Built-in scheduler for AI Lead Generation Agent

    Replaces n8n with native Python scheduling.
    Runs all automation tasks on configurable schedules.

    Usage:
        scheduler = AgentScheduler(agent_config, schedule_config)
        scheduler.start()  # Blocking
        # or
        await scheduler.start_async()  # Non-blocking
    """

    def __init__(
        self,
        agent_config: AgentConfig,
        schedule_config: Optional[ScheduleConfig] = None,
        notifier: Optional[Any] = None  # Notifier instance
    ):
        self.agent_config = agent_config
        self.schedule_config = schedule_config or ScheduleConfig()
        self.notifier = notifier

        self.agent = LeadGenerationAgent(agent_config)
        self.jobs: List[ScheduledJob] = []
        self.running = False
        self.stats = {
            "total_runs": 0,
            "leads_found": 0,
            "emails_sent": 0,
            "errors": 0,
            "started_at": None
        }

        self._setup_jobs()
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Setup graceful shutdown handlers"""
        def signal_handler(sig, frame):
            logger.info("Shutdown signal received, stopping scheduler...")
            self.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def _setup_jobs(self):
        """Setup scheduled jobs based on config"""
        config = self.schedule_config

        # Lead Search Job
        if config.search_enabled:
            self.jobs.append(ScheduledJob(
                name="lead_search",
                func=self._job_search_leads,
                schedule_type=ScheduleType.INTERVAL,
                interval_seconds=config.search_interval_hours * 3600
            ))

        # Follow-up Job
        if config.followup_enabled:
            self.jobs.append(ScheduledJob(
                name="follow_up",
                func=self._job_send_followups,
                schedule_type=ScheduleType.INTERVAL,
                interval_seconds=config.followup_interval_hours * 3600
            ))

        # Email Batch Job
        if config.email_enabled:
            self.jobs.append(ScheduledJob(
                name="email_batch",
                func=self._job_send_email_batch,
                schedule_type=ScheduleType.INTERVAL,
                interval_seconds=config.email_interval_minutes * 60
            ))

        # Daily Summary Job
        if config.notify_daily_summary:
            self.jobs.append(ScheduledJob(
                name="daily_summary",
                func=self._job_daily_summary,
                schedule_type=ScheduleType.DAILY,
                run_at=config.summary_time
            ))

        logger.info(f"Initialized {len(self.jobs)} scheduled jobs")

    async def _job_search_leads(self):
        """Job: Search for new leads"""
        config = self.schedule_config
        total_found = 0

        for keyword in config.default_keywords:
            for location in config.default_locations:
                logger.info(f"Searching: {keyword} in {location}")

                try:
                    result = await self.agent.run(
                        keyword=keyword,
                        location=location,
                        mode=AgentMode.GENERATE,
                        max_leads=config.max_leads_per_search
                    )

                    total_found += result.leads_added
                    self.stats["leads_found"] += result.leads_added

                    # Notify for hot leads
                    if self.notifier and config.notify_on_hot_lead:
                        for lead in result.leads:
                            if lead.get("lead_quality") == "hot":
                                await self.notifier.send_hot_lead_alert(lead)

                except Exception as e:
                    logger.error(f"Search error: {e}")
                    self.stats["errors"] += 1

                # Delay between searches
                await asyncio.sleep(5)

        logger.info(f"Search job complete: {total_found} new leads")
        return total_found

    async def _job_send_followups(self):
        """Job: Send follow-up emails"""
        logger.info("Checking for pending follow-ups...")

        try:
            result = await self.agent.run(
                keyword="",
                location="",
                mode=AgentMode.FOLLOW_UP
            )

            self.stats["emails_sent"] += result.emails_sent
            logger.info(f"Follow-up job complete: {result.emails_generated} emails")

            return result.emails_generated

        except Exception as e:
            logger.error(f"Follow-up error: {e}")
            self.stats["errors"] += 1
            return 0

    async def _job_send_email_batch(self):
        """Job: Send batch of pending emails"""
        # Get leads ready for outreach
        leads = self.agent.db.get_leads_for_outreach(
            limit=self.schedule_config.email_batch_size
        )

        if not leads:
            logger.debug("No leads ready for outreach")
            return 0

        logger.info(f"Sending emails to {len(leads)} leads")

        sent = 0
        for lead in leads:
            try:
                # Generate and "send" email
                # In production, integrate with actual email service
                self.agent.db.mark_lead_contacted(lead.id)
                sent += 1
                await asyncio.sleep(2)  # Rate limit

            except Exception as e:
                logger.error(f"Email send error for {lead.name}: {e}")

        self.stats["emails_sent"] += sent
        return sent

    async def _job_daily_summary(self):
        """Job: Send daily summary notification"""
        if not self.notifier:
            return

        stats = self.agent.get_stats()
        await self.notifier.send_daily_summary(stats, self.stats)
        logger.info("Daily summary sent")

    async def run_job(self, job: ScheduledJob):
        """Run a single job"""
        logger.info(f"Running job: {job.name}")
        job.last_run = datetime.now()
        self.stats["total_runs"] += 1

        try:
            if asyncio.iscoroutinefunction(job.func):
                result = await job.func()
            else:
                result = job.func()
            return result
        except Exception as e:
            logger.error(f"Job {job.name} failed: {e}")
            self.stats["errors"] += 1
            raise

    async def _scheduler_loop(self):
        """Main scheduler loop"""
        logger.info("Scheduler loop started")

        while self.running:
            for job in self.jobs:
                if job.should_run():
                    try:
                        await self.run_job(job)
                    except Exception as e:
                        logger.error(f"Job error: {e}")

            # Check every minute
            await asyncio.sleep(60)

    def start(self):
        """Start the scheduler (blocking)"""
        logger.info("Starting Agent Scheduler...")
        self.running = True
        self.stats["started_at"] = datetime.now()

        # Print startup info
        self._print_startup_info()

        # Run the event loop
        asyncio.run(self._scheduler_loop())

    async def start_async(self):
        """Start the scheduler (non-blocking, for integration)"""
        logger.info("Starting Agent Scheduler (async)...")
        self.running = True
        self.stats["started_at"] = datetime.now()

        # Start scheduler loop as background task
        asyncio.create_task(self._scheduler_loop())

    def stop(self):
        """Stop the scheduler"""
        logger.info("Stopping scheduler...")
        self.running = False

    def _print_startup_info(self):
        """Print startup information"""
        config = self.schedule_config

        print("\n" + "="*50)
        print("🤖 AI Lead Generation Agent - Scheduler")
        print("="*50)
        print(f"\n📋 Scheduled Jobs:")

        for job in self.jobs:
            status = "✅" if job.enabled else "❌"
            if job.schedule_type == ScheduleType.INTERVAL:
                interval = job.interval_seconds // 3600
                print(f"  {status} {job.name}: every {interval}h")
            elif job.schedule_type == ScheduleType.DAILY:
                print(f"  {status} {job.name}: daily at {job.run_at}")

        print(f"\n🎯 Targets:")
        print(f"  Keywords: {', '.join(config.default_keywords)}")
        print(f"  Locations: {', '.join(config.default_locations)}")

        print(f"\n📧 Email Settings:")
        print(f"  Batch size: {config.email_batch_size}")
        print(f"  Interval: {config.email_interval_minutes} min")

        print("\n" + "="*50)
        print("Press Ctrl+C to stop")
        print("="*50 + "\n")

    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status"""
        return {
            "running": self.running,
            "stats": self.stats,
            "jobs": [
                {
                    "name": job.name,
                    "enabled": job.enabled,
                    "last_run": job.last_run.isoformat() if job.last_run else None,
                    "schedule_type": job.schedule_type.value
                }
                for job in self.jobs
            ]
        }

    def run_job_now(self, job_name: str):
        """Manually trigger a job"""
        for job in self.jobs:
            if job.name == job_name:
                logger.info(f"Manually triggering job: {job_name}")
                asyncio.create_task(self.run_job(job))
                return True
        return False

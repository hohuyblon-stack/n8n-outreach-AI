#!/usr/bin/env python3
"""
Run the AI Lead Generation Agent Scheduler

This replaces n8n - runs all automation tasks natively in Python.

Usage:
    python run_scheduler.py                    # Run scheduler only
    python run_scheduler.py --with-dashboard   # Run with web dashboard
    python run_scheduler.py --dashboard-only   # Run dashboard only (no scheduler)
"""
import os
import sys
import asyncio
import threading
from pathlib import Path

import typer
import uvicorn
from dotenv import load_dotenv
from loguru import logger

# Load environment
load_dotenv()

# Add project root
sys.path.insert(0, str(Path(__file__).parent))

from src.agent.lead_agent import AgentConfig
from src.scheduler import AgentScheduler, ScheduleConfig
from src.notifications import Notifier, NotificationConfig
from src.database import Database
from src.dashboard import create_dashboard_app

app = typer.Typer(help="AI Lead Generation Agent Scheduler")


def get_agent_config() -> AgentConfig:
    """Get agent configuration from environment"""
    return AgentConfig(
        google_maps_api_key=os.getenv("GOOGLE_MAPS_API_KEY"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        sender_name=os.getenv("SENDER_NAME", "AI Agent"),
        company_name=os.getenv("COMPANY_NAME", "Your Company"),
        company_phone=os.getenv("COMPANY_PHONE", ""),
        company_website=os.getenv("COMPANY_WEBSITE", ""),
        database_url=os.getenv("DATABASE_URL", "sqlite:///./data/leads.db"),
        max_leads_per_search=int(os.getenv("MAX_LEADS_PER_SEARCH", "30")),
        daily_email_limit=int(os.getenv("EMAIL_DAILY_LIMIT", "100"))
    )


def get_schedule_config() -> ScheduleConfig:
    """Get schedule configuration from environment"""
    keywords = os.getenv("SCHEDULE_KEYWORDS", "spa,cafe,nha khoa").split(",")
    locations = os.getenv("SCHEDULE_LOCATIONS", "TP.HCM").split(",")

    return ScheduleConfig(
        search_enabled=os.getenv("SCHEDULE_SEARCH_ENABLED", "true").lower() == "true",
        search_interval_hours=int(os.getenv("SCHEDULE_SEARCH_HOURS", "24")),
        followup_enabled=os.getenv("SCHEDULE_FOLLOWUP_ENABLED", "true").lower() == "true",
        followup_interval_hours=int(os.getenv("SCHEDULE_FOLLOWUP_HOURS", "8")),
        email_enabled=os.getenv("SCHEDULE_EMAIL_ENABLED", "true").lower() == "true",
        email_batch_size=int(os.getenv("SCHEDULE_EMAIL_BATCH", "20")),
        email_interval_minutes=int(os.getenv("SCHEDULE_EMAIL_MINUTES", "30")),
        notify_daily_summary=os.getenv("NOTIFY_DAILY_SUMMARY", "true").lower() == "true",
        summary_time=os.getenv("SUMMARY_TIME", "18:00"),
        default_keywords=[k.strip() for k in keywords],
        default_locations=[l.strip() for l in locations],
        max_leads_per_search=int(os.getenv("MAX_LEADS_PER_SEARCH", "30"))
    )


def get_notification_config() -> NotificationConfig:
    """Get notification configuration from environment"""
    return NotificationConfig(
        telegram_enabled=os.getenv("TELEGRAM_ENABLED", "false").lower() == "true",
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
        discord_enabled=os.getenv("DISCORD_ENABLED", "false").lower() == "true",
        discord_webhook_url=os.getenv("DISCORD_WEBHOOK_URL", ""),
        notify_hot_leads=True,
        notify_replies=True,
        notify_errors=True,
        notify_daily_summary=True
    )


@app.command()
def run(
    with_dashboard: bool = typer.Option(False, "--with-dashboard", "-d", help="Run with web dashboard"),
    dashboard_only: bool = typer.Option(False, "--dashboard-only", help="Run dashboard only, no scheduler"),
    dashboard_port: int = typer.Option(8080, "--port", "-p", help="Dashboard port"),
    keywords: str = typer.Option(None, "--keywords", "-k", help="Override keywords (comma-separated)"),
    locations: str = typer.Option(None, "--locations", "-l", help="Override locations (comma-separated)")
):
    """
    Start the AI Lead Generation Agent Scheduler

    This is a standalone scheduler that replaces n8n.
    It runs automated tasks on configurable schedules.
    """
    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
        level="INFO"
    )
    logger.add(
        "logs/scheduler_{time}.log",
        rotation="1 day",
        retention="7 days",
        level="DEBUG"
    )

    # Get configurations
    agent_config = get_agent_config()
    schedule_config = get_schedule_config()
    notification_config = get_notification_config()

    # Override keywords/locations if provided
    if keywords:
        schedule_config.default_keywords = [k.strip() for k in keywords.split(",")]
    if locations:
        schedule_config.default_locations = [l.strip() for l in locations.split(",")]

    # Create notifier
    notifier = None
    if notification_config.telegram_enabled or notification_config.discord_enabled:
        notifier = Notifier(notification_config)
        logger.info("Notifications enabled")

    # Create scheduler
    scheduler = None
    if not dashboard_only:
        scheduler = AgentScheduler(
            agent_config=agent_config,
            schedule_config=schedule_config,
            notifier=notifier
        )

    # Dashboard only mode
    if dashboard_only:
        logger.info(f"Starting dashboard only on port {dashboard_port}")
        db = Database(agent_config.database_url)
        dashboard_app = create_dashboard_app(db, None)
        uvicorn.run(dashboard_app, host="0.0.0.0", port=dashboard_port)
        return

    # Run with dashboard
    if with_dashboard:
        logger.info(f"Starting scheduler with dashboard on port {dashboard_port}")

        # Create dashboard app
        db = Database(agent_config.database_url)
        dashboard_app = create_dashboard_app(db, scheduler)

        # Run dashboard in separate thread
        def run_dashboard():
            uvicorn.run(dashboard_app, host="0.0.0.0", port=dashboard_port, log_level="warning")

        dashboard_thread = threading.Thread(target=run_dashboard, daemon=True)
        dashboard_thread.start()

        logger.info(f"Dashboard available at http://localhost:{dashboard_port}")

    # Start scheduler (blocking)
    scheduler.start()


@app.command()
def status():
    """Check scheduler status"""
    # This would need IPC or file-based status checking
    # For now, just show configuration
    schedule_config = get_schedule_config()

    print("\n📋 Scheduler Configuration")
    print("="*40)
    print(f"Keywords: {', '.join(schedule_config.default_keywords)}")
    print(f"Locations: {', '.join(schedule_config.default_locations)}")
    print(f"\nSchedule:")
    print(f"  Search: Every {schedule_config.search_interval_hours}h")
    print(f"  Follow-up: Every {schedule_config.followup_interval_hours}h")
    print(f"  Email batch: Every {schedule_config.email_interval_minutes}min")
    print(f"  Daily summary: {schedule_config.summary_time}")


@app.command()
def test_notify(
    channel: str = typer.Option("all", "--channel", "-c", help="Channel: telegram, discord, or all")
):
    """Test notification channels"""
    notification_config = get_notification_config()
    notifier = Notifier(notification_config)

    async def send_test():
        result = await notifier.send_custom(
            message="🧪 This is a test notification from AI Lead Generation Agent!",
            title="Test Notification"
        )
        return result

    result = asyncio.run(send_test())

    if result:
        print("✅ Test notification sent successfully!")
    else:
        print("❌ Failed to send test notification. Check your configuration.")


if __name__ == "__main__":
    app()

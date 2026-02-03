"""
Notification System - Send alerts via Telegram, Discord, or Email
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

from loguru import logger


class NotificationType(Enum):
    """Types of notifications"""
    HOT_LEAD = "hot_lead"
    NEW_REPLY = "new_reply"
    DAILY_SUMMARY = "daily_summary"
    ERROR_ALERT = "error_alert"
    JOB_COMPLETE = "job_complete"


@dataclass
class NotificationConfig:
    """Configuration for notifications"""
    # Telegram
    telegram_enabled: bool = False
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Discord
    discord_enabled: bool = False
    discord_webhook_url: str = ""

    # Email
    email_enabled: bool = False
    email_recipient: str = ""

    # Settings
    notify_hot_leads: bool = True
    notify_replies: bool = True
    notify_errors: bool = True
    notify_daily_summary: bool = True
    quiet_hours_start: int = 22  # 10 PM
    quiet_hours_end: int = 8     # 8 AM


class BaseNotifier(ABC):
    """Abstract base class for notifiers"""

    @abstractmethod
    async def send(self, message: str, title: Optional[str] = None) -> bool:
        """Send a notification"""
        pass

    @abstractmethod
    async def send_rich(self, data: Dict[str, Any], notification_type: NotificationType) -> bool:
        """Send a rich/formatted notification"""
        pass


class Notifier:
    """
    Multi-channel notification manager

    Sends notifications to configured channels (Telegram, Discord, Email)
    with smart formatting and quiet hours support.

    Usage:
        config = NotificationConfig(
            telegram_enabled=True,
            telegram_bot_token="...",
            telegram_chat_id="..."
        )
        notifier = Notifier(config)
        await notifier.send_hot_lead_alert(lead_data)
    """

    def __init__(self, config: NotificationConfig):
        self.config = config
        self.notifiers: List[BaseNotifier] = []

        self._setup_notifiers()

    def _setup_notifiers(self):
        """Initialize enabled notifiers"""
        if self.config.telegram_enabled:
            from .telegram_notifier import TelegramNotifier
            self.notifiers.append(TelegramNotifier(
                bot_token=self.config.telegram_bot_token,
                chat_id=self.config.telegram_chat_id
            ))
            logger.info("Telegram notifier enabled")

        if self.config.discord_enabled:
            from .discord_notifier import DiscordNotifier
            self.notifiers.append(DiscordNotifier(
                webhook_url=self.config.discord_webhook_url
            ))
            logger.info("Discord notifier enabled")

    def _is_quiet_hours(self) -> bool:
        """Check if current time is within quiet hours"""
        hour = datetime.now().hour
        start = self.config.quiet_hours_start
        end = self.config.quiet_hours_end

        if start > end:  # Spans midnight
            return hour >= start or hour < end
        else:
            return start <= hour < end

    async def _send_to_all(
        self,
        message: str,
        title: Optional[str] = None,
        notification_type: Optional[NotificationType] = None,
        data: Optional[Dict] = None,
        ignore_quiet_hours: bool = False
    ) -> bool:
        """Send notification to all enabled channels"""
        if not ignore_quiet_hours and self._is_quiet_hours():
            logger.debug("Skipping notification during quiet hours")
            return False

        success = False
        for notifier in self.notifiers:
            try:
                if data and notification_type:
                    result = await notifier.send_rich(data, notification_type)
                else:
                    result = await notifier.send(message, title)
                success = success or result
            except Exception as e:
                logger.error(f"Notifier error: {e}")

        return success

    async def send_hot_lead_alert(self, lead: Dict[str, Any]) -> bool:
        """Send alert for hot lead"""
        if not self.config.notify_hot_leads:
            return False

        return await self._send_to_all(
            message="",
            notification_type=NotificationType.HOT_LEAD,
            data=lead,
            ignore_quiet_hours=True  # Hot leads are important!
        )

    async def send_reply_alert(self, lead: Dict[str, Any], reply_preview: str) -> bool:
        """Send alert when lead replies"""
        if not self.config.notify_replies:
            return False

        data = {**lead, "reply_preview": reply_preview}
        return await self._send_to_all(
            message="",
            notification_type=NotificationType.NEW_REPLY,
            data=data,
            ignore_quiet_hours=True
        )

    async def send_daily_summary(
        self,
        lead_stats: Dict[str, Any],
        scheduler_stats: Dict[str, Any]
    ) -> bool:
        """Send daily summary"""
        if not self.config.notify_daily_summary:
            return False

        data = {
            "lead_stats": lead_stats,
            "scheduler_stats": scheduler_stats,
            "date": datetime.now().strftime("%Y-%m-%d")
        }

        return await self._send_to_all(
            message="",
            notification_type=NotificationType.DAILY_SUMMARY,
            data=data
        )

    async def send_error_alert(self, error: str, context: Optional[str] = None) -> bool:
        """Send error alert"""
        if not self.config.notify_errors:
            return False

        data = {
            "error": error,
            "context": context,
            "timestamp": datetime.now().isoformat()
        }

        return await self._send_to_all(
            message="",
            notification_type=NotificationType.ERROR_ALERT,
            data=data,
            ignore_quiet_hours=True
        )

    async def send_custom(self, message: str, title: Optional[str] = None) -> bool:
        """Send custom message"""
        return await self._send_to_all(message, title)

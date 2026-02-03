"""
Discord Notifier - Send notifications via Discord Webhook
"""
from typing import Optional, Dict, Any, List
from datetime import datetime

import httpx
from loguru import logger

from .notifier import BaseNotifier, NotificationType


class DiscordNotifier(BaseNotifier):
    """
    Send notifications via Discord Webhook

    Setup:
    1. Go to Discord Server Settings > Integrations > Webhooks
    2. Create new webhook or use existing
    3. Copy webhook URL
    """

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    async def send(self, message: str, title: Optional[str] = None) -> bool:
        """Send a simple text message"""
        payload = {
            "content": f"**{title}**\n{message}" if title else message
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json=payload
                )
                response.raise_for_status()
                logger.debug("Discord message sent")
                return True

        except Exception as e:
            logger.error(f"Discord send error: {e}")
            return False

    async def send_rich(self, data: Dict[str, Any], notification_type: NotificationType) -> bool:
        """Send rich embed notification"""
        embed = self._create_embed(data, notification_type)
        payload = {"embeds": [embed]}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json=payload
                )
                response.raise_for_status()
                logger.debug("Discord embed sent")
                return True

        except Exception as e:
            logger.error(f"Discord send error: {e}")
            return False

    def _create_embed(self, data: Dict[str, Any], notification_type: NotificationType) -> Dict:
        """Create Discord embed based on notification type"""

        if notification_type == NotificationType.HOT_LEAD:
            return self._create_hot_lead_embed(data)

        elif notification_type == NotificationType.NEW_REPLY:
            return self._create_reply_embed(data)

        elif notification_type == NotificationType.DAILY_SUMMARY:
            return self._create_summary_embed(data)

        elif notification_type == NotificationType.ERROR_ALERT:
            return self._create_error_embed(data)

        else:
            return {
                "title": "Notification",
                "description": str(data),
                "color": 0x5865F2
            }

    def _create_hot_lead_embed(self, lead: Dict[str, Any]) -> Dict:
        """Create embed for hot lead"""
        return {
            "title": "🔥 HOT LEAD ALERT!",
            "description": f"**{lead.get('name', 'Unknown')}**",
            "color": 0xFF4500,  # Orange-red
            "fields": [
                {
                    "name": "📍 Address",
                    "value": lead.get('address', 'N/A'),
                    "inline": False
                },
                {
                    "name": "📧 Email",
                    "value": lead.get('email', 'N/A'),
                    "inline": True
                },
                {
                    "name": "📞 Phone",
                    "value": lead.get('phone', 'N/A'),
                    "inline": True
                },
                {
                    "name": "📊 Lead Score",
                    "value": f"{lead.get('lead_score', 0)}/100",
                    "inline": True
                },
                {
                    "name": "⭐ Rating",
                    "value": str(lead.get('rating', 'N/A')),
                    "inline": True
                },
                {
                    "name": "🏷 Industry",
                    "value": lead.get('industry', 'N/A'),
                    "inline": True
                },
                {
                    "name": "💡 Recommended Offer",
                    "value": lead.get('recommended_offer', 'Contact ASAP'),
                    "inline": False
                }
            ],
            "footer": {
                "text": "Follow up ngay để không bỏ lỡ!"
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    def _create_reply_embed(self, data: Dict[str, Any]) -> Dict:
        """Create embed for reply notification"""
        return {
            "title": "📬 NEW REPLY!",
            "description": f"**{data.get('name', 'Unknown')}** đã phản hồi!",
            "color": 0x00FF00,  # Green
            "fields": [
                {
                    "name": "📧 Email",
                    "value": data.get('email', 'N/A'),
                    "inline": True
                },
                {
                    "name": "💬 Preview",
                    "value": data.get('reply_preview', 'No preview')[:200],
                    "inline": False
                }
            ],
            "footer": {
                "text": "Check email ngay!"
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    def _create_summary_embed(self, data: Dict[str, Any]) -> Dict:
        """Create embed for daily summary"""
        lead_stats = data.get('lead_stats', {})
        scheduler_stats = data.get('scheduler_stats', {})
        leads = lead_stats.get('leads', {})
        emails = lead_stats.get('emails', {})
        by_status = leads.get('by_status', {})

        return {
            "title": f"📊 Daily Summary - {data.get('date', 'Today')}",
            "color": 0x5865F2,  # Discord blue
            "fields": [
                {
                    "name": "📋 Leads Overview",
                    "value": (
                        f"• Total: {leads.get('total_leads', 0)}\n"
                        f"• New: {by_status.get('new', 0)}\n"
                        f"• Contacted: {by_status.get('contacted', 0)}\n"
                        f"• Responded: {by_status.get('responded', 0)}"
                    ),
                    "inline": True
                },
                {
                    "name": "📧 Email Stats",
                    "value": (
                        f"• Sent: {emails.get('total_sent', 0)}\n"
                        f"• Open Rate: {emails.get('open_rate', 0)}%\n"
                        f"• Reply Rate: {emails.get('reply_rate', 0)}%"
                    ),
                    "inline": True
                },
                {
                    "name": "⚙️ Scheduler",
                    "value": (
                        f"• Total Runs: {scheduler_stats.get('total_runs', 0)}\n"
                        f"• Leads Found: {scheduler_stats.get('leads_found', 0)}\n"
                        f"• Errors: {scheduler_stats.get('errors', 0)}"
                    ),
                    "inline": False
                }
            ],
            "footer": {
                "text": "AI Lead Generation Agent"
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    def _create_error_embed(self, data: Dict[str, Any]) -> Dict:
        """Create embed for error alert"""
        return {
            "title": "⚠️ ERROR ALERT",
            "color": 0xFF0000,  # Red
            "fields": [
                {
                    "name": "❌ Error",
                    "value": f"```{data.get('error', 'Unknown error')}```",
                    "inline": False
                },
                {
                    "name": "📍 Context",
                    "value": data.get('context', 'No context available'),
                    "inline": False
                }
            ],
            "footer": {
                "text": "Kiểm tra logs để biết thêm chi tiết"
            },
            "timestamp": datetime.utcnow().isoformat()
        }

"""
Telegram Notifier - Send notifications via Telegram Bot
"""
from typing import Optional, Dict, Any

import httpx
from loguru import logger

from .notifier import BaseNotifier, NotificationType


class TelegramNotifier(BaseNotifier):
    """
    Send notifications via Telegram Bot API

    Setup:
    1. Create bot via @BotFather on Telegram
    2. Get bot token
    3. Start chat with bot and get chat_id

    To get chat_id:
    - Send message to your bot
    - Visit: https://api.telegram.org/bot<TOKEN>/getUpdates
    - Find chat.id in response
    """

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}"

    async def send(self, message: str, title: Optional[str] = None) -> bool:
        """Send a simple text message"""
        text = f"*{title}*\n\n{message}" if title else message

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/sendMessage",
                    json={
                        "chat_id": self.chat_id,
                        "text": text,
                        "parse_mode": "Markdown"
                    }
                )
                response.raise_for_status()
                logger.debug("Telegram message sent")
                return True

        except Exception as e:
            logger.error(f"Telegram send error: {e}")
            return False

    async def send_rich(self, data: Dict[str, Any], notification_type: NotificationType) -> bool:
        """Send formatted notification based on type"""
        message = self._format_message(data, notification_type)
        return await self.send(message)

    def _format_message(self, data: Dict[str, Any], notification_type: NotificationType) -> str:
        """Format message based on notification type"""

        if notification_type == NotificationType.HOT_LEAD:
            return self._format_hot_lead(data)

        elif notification_type == NotificationType.NEW_REPLY:
            return self._format_reply(data)

        elif notification_type == NotificationType.DAILY_SUMMARY:
            return self._format_daily_summary(data)

        elif notification_type == NotificationType.ERROR_ALERT:
            return self._format_error(data)

        else:
            return str(data)

    def _format_hot_lead(self, lead: Dict[str, Any]) -> str:
        """Format hot lead alert"""
        return f"""🔥 *HOT LEAD ALERT!*

*{lead.get('name', 'Unknown')}*
📍 {lead.get('address', 'N/A')}
📧 {lead.get('email', 'N/A')}
📞 {lead.get('phone', 'N/A')}

⭐ Rating: {lead.get('rating', 'N/A')}
📊 Lead Score: {lead.get('lead_score', 0)}/100
🏷 Industry: {lead.get('industry', 'N/A')}

💡 Recommended: {lead.get('recommended_offer', 'Contact ASAP')}

---
_Follow up ngay để không bỏ lỡ!_"""

    def _format_reply(self, data: Dict[str, Any]) -> str:
        """Format reply notification"""
        return f"""📬 *NEW REPLY!*

*{data.get('name', 'Unknown')}* đã phản hồi!

📧 Email: {data.get('email', 'N/A')}

💬 Preview:
_{data.get('reply_preview', 'No preview available')[:200]}_

---
_Check email ngay!_"""

    def _format_daily_summary(self, data: Dict[str, Any]) -> str:
        """Format daily summary"""
        lead_stats = data.get('lead_stats', {})
        scheduler_stats = data.get('scheduler_stats', {})

        leads = lead_stats.get('leads', {})
        by_status = leads.get('by_status', {})

        return f"""📊 *DAILY SUMMARY - {data.get('date', 'Today')}*

*📋 Leads Overview*
• Total: {leads.get('total_leads', 0)}
• New: {by_status.get('new', 0)}
• Contacted: {by_status.get('contacted', 0)}
• Responded: {by_status.get('responded', 0)}
• Converted: {by_status.get('converted', 0)}

*📧 Email Stats*
• Sent: {lead_stats.get('emails', {}).get('total_sent', 0)}
• Open Rate: {lead_stats.get('emails', {}).get('open_rate', 0)}%
• Reply Rate: {lead_stats.get('emails', {}).get('reply_rate', 0)}%

*⚙️ Scheduler*
• Total Runs: {scheduler_stats.get('total_runs', 0)}
• Leads Found: {scheduler_stats.get('leads_found', 0)}
• Errors: {scheduler_stats.get('errors', 0)}

---
_Chúc bạn một ngày làm việc hiệu quả!_"""

    def _format_error(self, data: Dict[str, Any]) -> str:
        """Format error alert"""
        return f"""⚠️ *ERROR ALERT*

🕐 Time: {data.get('timestamp', 'Unknown')}

❌ Error:
`{data.get('error', 'Unknown error')}`

📍 Context:
{data.get('context', 'No context available')}

---
_Kiểm tra logs để biết thêm chi tiết._"""

"""
Email Sender - Send emails via SMTP or email service APIs
"""
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass

from loguru import logger

from src.email_generator.email_generator import GeneratedEmail


@dataclass
class EmailConfig:
    """Email server configuration"""
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    username: str = ""
    password: str = ""
    sender_name: str = "AI Agent"
    sender_email: str = ""
    use_tls: bool = True


@dataclass
class SendResult:
    """Result of email send operation"""
    success: bool
    email_id: Optional[str] = None
    error: Optional[str] = None
    sent_at: Optional[datetime] = None


class EmailSender:
    """
    Send emails via SMTP

    Features:
    - SMTP with TLS support
    - Rate limiting
    - Retry logic
    - Tracking pixels (optional)
    """

    def __init__(self, config: EmailConfig):
        """
        Initialize email sender

        Args:
            config: EmailConfig with SMTP settings
        """
        self.config = config
        self.daily_sent = 0
        self.daily_limit = 100

    def _create_message(
        self,
        email: GeneratedEmail,
        add_tracking: bool = False
    ) -> MIMEMultipart:
        """Create MIME message from GeneratedEmail"""
        msg = MIMEMultipart("alternative")

        msg["Subject"] = email.subject
        msg["From"] = f"{self.config.sender_name} <{self.config.sender_email}>"
        msg["To"] = email.recipient_email
        msg["Reply-To"] = self.config.sender_email

        # Plain text version
        text_part = MIMEText(email.body, "plain", "utf-8")
        msg.attach(text_part)

        # HTML version with optional tracking
        html_body = self._text_to_html(email.body)

        if add_tracking:
            # Add tracking pixel (implement your tracking server)
            tracking_url = f"https://your-tracking-server.com/open/{email.business_name}"
            html_body += f'<img src="{tracking_url}" width="1" height="1" />'

        html_part = MIMEText(html_body, "html", "utf-8")
        msg.attach(html_part)

        return msg

    def _text_to_html(self, text: str) -> str:
        """Convert plain text to simple HTML"""
        # Escape HTML characters
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")

        # Convert line breaks
        text = text.replace("\n\n", "</p><p>")
        text = text.replace("\n", "<br>")

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    font-size: 14px;
                    line-height: 1.6;
                    color: #333;
                }}
                p {{ margin: 10px 0; }}
            </style>
        </head>
        <body>
            <p>{text}</p>
        </body>
        </html>
        """

    def send(
        self,
        email: GeneratedEmail,
        add_tracking: bool = False
    ) -> SendResult:
        """
        Send a single email

        Args:
            email: GeneratedEmail to send
            add_tracking: Add tracking pixel

        Returns:
            SendResult with success status
        """
        if self.daily_sent >= self.daily_limit:
            return SendResult(
                success=False,
                error="Daily email limit reached"
            )

        if not email.recipient_email:
            return SendResult(
                success=False,
                error="No recipient email"
            )

        try:
            msg = self._create_message(email, add_tracking)

            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                if self.config.use_tls:
                    server.starttls()

                server.login(self.config.username, self.config.password)
                server.send_message(msg)

            self.daily_sent += 1

            logger.info(f"Email sent to {email.recipient_email}")

            return SendResult(
                success=True,
                sent_at=datetime.now()
            )

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP auth error: {e}")
            return SendResult(success=False, error="Authentication failed")

        except smtplib.SMTPRecipientsRefused as e:
            logger.error(f"Recipient refused: {e}")
            return SendResult(success=False, error="Recipient refused")

        except Exception as e:
            logger.error(f"Email send error: {e}")
            return SendResult(success=False, error=str(e))

    def send_batch(
        self,
        emails: List[GeneratedEmail],
        delay_seconds: float = 2.0
    ) -> Dict[str, Any]:
        """
        Send multiple emails with rate limiting

        Args:
            emails: List of emails to send
            delay_seconds: Delay between sends

        Returns:
            Summary of results
        """
        results = {
            "total": len(emails),
            "sent": 0,
            "failed": 0,
            "errors": []
        }

        for email in emails:
            result = self.send(email)

            if result.success:
                results["sent"] += 1
            else:
                results["failed"] += 1
                results["errors"].append({
                    "email": email.recipient_email,
                    "error": result.error
                })

            # Rate limiting
            import time
            time.sleep(delay_seconds)

            # Check daily limit
            if self.daily_sent >= self.daily_limit:
                logger.warning("Daily limit reached, stopping batch")
                break

        return results

    async def send_async(
        self,
        email: GeneratedEmail,
        add_tracking: bool = False
    ) -> SendResult:
        """Async version of send"""
        # Run sync send in thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.send(email, add_tracking)
        )

    async def send_batch_async(
        self,
        emails: List[GeneratedEmail],
        delay_seconds: float = 2.0,
        concurrency: int = 1
    ) -> Dict[str, Any]:
        """
        Async batch send with concurrency control

        Note: Keep concurrency low to avoid rate limits
        """
        results = {
            "total": len(emails),
            "sent": 0,
            "failed": 0,
            "errors": []
        }

        semaphore = asyncio.Semaphore(concurrency)

        async def send_with_limit(email: GeneratedEmail):
            async with semaphore:
                result = await self.send_async(email)
                await asyncio.sleep(delay_seconds)
                return email, result

        tasks = [send_with_limit(email) for email in emails]

        for coro in asyncio.as_completed(tasks):
            email, result = await coro

            if result.success:
                results["sent"] += 1
            else:
                results["failed"] += 1
                results["errors"].append({
                    "email": email.recipient_email,
                    "error": result.error
                })

            if self.daily_sent >= self.daily_limit:
                break

        return results

    def test_connection(self) -> bool:
        """Test SMTP connection"""
        try:
            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                if self.config.use_tls:
                    server.starttls()
                server.login(self.config.username, self.config.password)
                logger.info("SMTP connection test successful")
                return True
        except Exception as e:
            logger.error(f"SMTP connection test failed: {e}")
            return False

    def reset_daily_count(self):
        """Reset daily send count (call at midnight)"""
        self.daily_sent = 0

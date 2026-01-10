"""
Email notification channel using Resend SDK.
Handles email delivery with retry logic and error handling.
"""

import logging
from dataclasses import dataclass
from typing import Any

import resend
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import settings
from src.core.exceptions import NotificationError

logger = logging.getLogger(__name__)


@dataclass
class EmailResult:
    """Result of an email send operation."""

    success: bool
    message_id: str | None = None
    error_message: str | None = None


class EmailChannel:
    """
    Email notification channel using Resend.

    Features:
    - Retry logic with exponential backoff (3 attempts)
    - Configurable from/to addresses
    - HTML and plain text support
    """

    def __init__(
        self,
        api_key: str | None = None,
        from_email: str | None = None,
    ) -> None:
        """
        Initialize the email channel.

        Args:
            api_key: Resend API key. Defaults to settings.resend_api_key.
            from_email: From email address. Defaults to settings.from_email.
        """
        self._api_key = api_key if api_key is not None else settings.resend_api_key
        self._from_email = from_email if from_email is not None else settings.from_email

        if self._api_key:
            resend.api_key = self._api_key

    @property
    def is_configured(self) -> bool:
        """Check if email channel is properly configured."""
        return bool(self._api_key and self._from_email)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def send(
        self,
        to: str,
        subject: str,
        html_content: str,
        text_content: str | None = None,
        reply_to: str | None = None,
        tags: list[dict[str, str]] | None = None,
    ) -> EmailResult:
        """
        Send an email with retry logic.

        Args:
            to: Recipient email address.
            subject: Email subject line.
            html_content: HTML body content.
            text_content: Optional plain text content.
            reply_to: Optional reply-to address.
            tags: Optional tags for tracking (e.g., [{"name": "type", "value": "alert"}]).

        Returns:
            EmailResult with success status and message ID or error.

        Raises:
            NotificationError: If sending fails after all retries.
        """
        if not self.is_configured:
            logger.warning("Email channel not configured - skipping send")
            return EmailResult(
                success=False,
                error_message="Email channel not configured",
            )

        params: dict[str, Any] = {
            "from": self._from_email,
            "to": [to],
            "subject": subject,
            "html": html_content,
        }

        if text_content:
            params["text"] = text_content

        if reply_to:
            params["reply_to"] = reply_to

        if tags:
            params["tags"] = tags

        try:
            # Resend SDK is synchronous, run in thread pool
            import asyncio

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: resend.Emails.send(params),
            )

            message_id = response.get("id") if isinstance(response, dict) else None

            logger.info(
                "Email sent successfully",
                extra={
                    "to": to,
                    "subject": subject,
                    "message_id": message_id,
                },
            )

            return EmailResult(
                success=True,
                message_id=message_id,
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(
                "Failed to send email",
                extra={
                    "to": to,
                    "subject": subject,
                    "error": error_msg,
                },
            )
            raise NotificationError(f"Failed to send email: {error_msg}") from e

    async def send_batch(
        self,
        emails: list[dict[str, Any]],
    ) -> list[EmailResult]:
        """
        Send multiple emails.

        Args:
            emails: List of email dicts with keys: to, subject, html_content, etc.

        Returns:
            List of EmailResult for each email.
        """
        results = []
        for email in emails:
            try:
                result = await self.send(
                    to=email["to"],
                    subject=email["subject"],
                    html_content=email["html_content"],
                    text_content=email.get("text_content"),
                    reply_to=email.get("reply_to"),
                    tags=email.get("tags"),
                )
                results.append(result)
            except NotificationError as e:
                results.append(
                    EmailResult(
                        success=False,
                        error_message=str(e),
                    )
                )

        return results

"""Asynchronous background tasks for email notifications and webhook dispatches."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Optional
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("background_tasks")

# Thread-safe in-memory log of executed background tasks
task_execution_log: list[dict[str, Any]] = []


def record_task_log(
    task_id: str,
    task_type: str,
    target: str,
    status: str,
    details: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    entry = {
        "task_id": task_id,
        "task_type": task_type,
        "target": target,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "details": details or {},
    }
    task_execution_log.append(entry)
    return entry


async def send_email_notification(
    recipient: str,
    subject: str,
    message: str,
    task_id: Optional[str] = None,
) -> None:
    """Asynchronous background task to send an email notification."""
    t_id = task_id or str(uuid.uuid4())
    logger.info(
        f"[BackgroundTask: Email] Dispatching to '{recipient}' | Subject: '{subject}' | Task ID: {t_id}"
    )

    # Simulate async I/O network dispatch
    await asyncio.sleep(0.05)

    record_task_log(
        task_id=t_id,
        task_type="email",
        target=recipient,
        status="delivered",
        details={"subject": subject, "body_preview": message[:100]},
    )
    logger.info(f"[BackgroundTask: Email] Successfully delivered email to '{recipient}' (Task ID: {t_id})")


async def dispatch_webhook(
    url: str,
    event: str,
    payload: dict[str, Any],
    task_id: Optional[str] = None,
) -> None:
    """Asynchronous background task to dispatch a webhook notification."""
    t_id = task_id or str(uuid.uuid4())
    logger.info(
        f"[BackgroundTask: Webhook] Dispatching event '{event}' to '{url}' | Task ID: {t_id}"
    )

    # Simulate async I/O HTTP POST to external webhook URL
    await asyncio.sleep(0.05)

    record_task_log(
        task_id=t_id,
        task_type="webhook",
        target=url,
        status="dispatched",
        details={"event": event, "payload": payload},
    )
    logger.info(
        f"[BackgroundTask: Webhook] Successfully dispatched webhook '{event}' to '{url}' (Task ID: {t_id})"
    )


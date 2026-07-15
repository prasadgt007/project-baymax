"""
calendar_client.py
──────────────────
Thin wrapper around Composio's Google Calendar toolkit.

Creates a Google Calendar event when a patient books an appointment. This is
**best-effort**: the slot is already reserved in Supabase before we get here, so
a calendar failure must never break the booking — we simply report the outcome.

Requires two environment variables (already in .env):
  - COMPOSIO_API_KEY   : Composio API key
  - COMPOSIO_USER_ID   : the Composio entity/user whose Google Calendar is connected
"""

import os
from typing import Optional

# Composio action slug for creating a calendar event (verified against the
# connected GOOGLECALENDAR toolkit — requires `start_datetime`).
_CREATE_EVENT = "GOOGLECALENDAR_CREATE_EVENT"

# Default timezone for the demo. IANA name. Change to suit the hospital's locale.
_DEFAULT_TZ = os.environ.get("BAYMAX_TIMEZONE", "Asia/Kolkata")


def _event_payload(data) -> dict:
    """Return the inner Google event resource from Composio's response data."""
    if not isinstance(data, dict):
        return {}
    for key in ("response_data", "data", "result"):
        inner = data.get(key)
        if isinstance(inner, dict):
            return inner
    return data


def _extract_event_link(data) -> Optional[str]:
    """Best-effort pull of the event's htmlLink from Composio's response data."""
    p = _event_payload(data)
    return p.get("htmlLink") or p.get("hangoutLink")


def _extract_event_id(data) -> Optional[str]:
    """Best-effort pull of the event's id from Composio's response data."""
    return _event_payload(data).get("id")


def create_appointment_event(
    *,
    start_datetime: str,
    summary: str,
    description: str = "",
    duration_minutes: int = 60,
    timezone: Optional[str] = None,
) -> dict:
    """
    Create a Google Calendar event for a booked appointment.

    Args:
        start_datetime: ISO 8601 start time, e.g. "2026-07-16T09:00:00".
        summary:        Event title.
        description:    Event body.
        duration_minutes: Appointment length in minutes.
        timezone:       IANA timezone name; defaults to BAYMAX_TIMEZONE / Asia/Kolkata.

    Returns:
        {"success": bool, "event_id": str|None, "event_link": str|None, "error": str|None}
    """
    if not start_datetime:
        return {"success": False, "event_id": None, "event_link": None, "error": "Missing start_datetime"}

    api_key = os.environ.get("COMPOSIO_API_KEY")
    user_id = os.environ.get("COMPOSIO_USER_ID")
    if not api_key or not user_id:
        return {
            "success": False,
            "event_id": None,
            "event_link": None,
            "error": "COMPOSIO_API_KEY / COMPOSIO_USER_ID not configured",
        }

    try:
        from composio import Composio

        client = Composio(api_key=api_key)

        # Composio splits duration into hours + minutes; the minutes field must be 0-59.
        hours, minutes = divmod(int(duration_minutes or 60), 60)

        arguments = {
            "start_datetime": start_datetime,
            "summary": summary,
            "description": description,
            "timezone": timezone or _DEFAULT_TZ,
            "calendar_id": "primary",
            "event_duration_minutes": minutes,
        }
        if hours:
            arguments["event_duration_hour"] = hours

        resp = client.tools.execute(
            _CREATE_EVENT,
            arguments,
            user_id=user_id,
            # The connected toolkit has no pinned version in our Composio config;
            # skip the version check so manual execution works. Safe for the demo.
            dangerously_skip_version_check=True,
        )

        # ToolExecutionResponse may be an object or a dict depending on SDK build.
        successful = getattr(resp, "successful", None)
        data = getattr(resp, "data", None)
        error = getattr(resp, "error", None)
        if successful is None and isinstance(resp, dict):
            successful = resp.get("successful", resp.get("success"))
            data = resp.get("data")
            error = resp.get("error")

        if successful:
            return {
                "success": True,
                "event_id": _extract_event_id(data),
                "event_link": _extract_event_link(data),
                "error": None,
            }
        return {"success": False, "event_id": None, "event_link": None, "error": str(error or "Unknown Composio error")}

    except Exception as e:
        return {"success": False, "event_id": None, "event_link": None, "error": str(e)}


def delete_calendar_event(event_id: str, calendar_id: str = "primary") -> dict:
    """
    Delete a previously created Google Calendar event (used when an appointment is
    cancelled or rescheduled). Best-effort — returns success/error, never raises.

    Returns:
        {"success": bool, "error": str|None}
    """
    if not event_id:
        return {"success": False, "error": "Missing event_id"}

    api_key = os.environ.get("COMPOSIO_API_KEY")
    user_id = os.environ.get("COMPOSIO_USER_ID")
    if not api_key or not user_id:
        return {"success": False, "error": "COMPOSIO_API_KEY / COMPOSIO_USER_ID not configured"}

    try:
        from composio import Composio

        client = Composio(api_key=api_key)
        resp = client.tools.execute(
            "GOOGLECALENDAR_DELETE_EVENT",
            {"event_id": event_id, "calendar_id": calendar_id},
            user_id=user_id,
            dangerously_skip_version_check=True,
        )
        successful = getattr(resp, "successful", None)
        error = getattr(resp, "error", None)
        if successful is None and isinstance(resp, dict):
            successful = resp.get("successful", resp.get("success"))
            error = resp.get("error")
        return {"success": bool(successful), "error": None if successful else str(error or "Unknown error")}

    except Exception as e:
        return {"success": False, "error": str(e)}

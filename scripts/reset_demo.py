"""
scripts/reset_demo.py
─────────────────────
Reset Baymax to a clean state between demo runs:
  1. Un-book every hospital slot (frees scheduling; clears stored calendar event ids).
  2. Best-effort: delete the Google Calendar events Baymax created (summary starts with
     "Doctor Appointment") in the next 14 days, so the demo calendar is clean too.

It does NOT touch patients or their baseline records — only bookings/calendar.

Run from the repo root:
    uv run python scripts/reset_demo.py
"""

import os
import sys
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

load_dotenv()


def reset_bookings() -> int:
    import psycopg

    uri = os.environ.get("SUPABASE_DB_URI")
    if not uri:
        print("[FAIL] SUPABASE_DB_URI not set in .env", file=sys.stderr)
        raise SystemExit(1)

    with psycopg.connect(uri) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE hospital_slots "
                "SET is_booked = false, booked_patient_id = NULL, calendar_event_id = NULL "
                "WHERE is_booked = true;"
            )
            freed = cur.rowcount
        conn.commit()
    print(f"[ OK ] Un-booked {freed} slot(s)")
    return freed


def clear_calendar() -> None:
    api_key = os.environ.get("COMPOSIO_API_KEY")
    user_id = os.environ.get("COMPOSIO_USER_ID")
    if not api_key or not user_id:
        print("[SKIP] Composio not configured — leaving calendar untouched")
        return

    try:
        from composio import Composio

        client = Composio(api_key=api_key)
        now = datetime.now(timezone.utc)
        resp = client.tools.execute(
            "GOOGLECALENDAR_EVENTS_LIST",
            {
                "calendar_id": "primary",
                "timeMin": now.strftime("%Y-%m-%dT00:00:00Z"),
                "timeMax": (now + timedelta(days=14)).strftime("%Y-%m-%dT00:00:00Z"),
            },
            user_id=user_id,
            dangerously_skip_version_check=True,
        )

        def find_items(d):
            if isinstance(d, dict):
                if isinstance(d.get("items"), list):
                    return d["items"]
                for v in d.values():
                    r = find_items(v)
                    if r is not None:
                        return r
            return None

        events = find_items(resp.get("data")) or []
        deleted = 0
        for ev in events:
            summary = ev.get("summary") or ""
            if summary.startswith("Doctor Appointment"):  # Baymax-created events
                client.tools.execute(
                    "GOOGLECALENDAR_DELETE_EVENT",
                    {"event_id": ev.get("id"), "calendar_id": "primary"},
                    user_id=user_id,
                    dangerously_skip_version_check=True,
                )
                deleted += 1
        print(f"[ OK ] Deleted {deleted} Baymax calendar event(s)")
    except Exception as e:
        print(f"[WARN] Calendar cleanup skipped: {e}")


if __name__ == "__main__":
    print("Resetting Baymax demo state...")
    reset_bookings()
    clear_calendar()
    print("\n[DONE] Ready for a fresh demo run.")

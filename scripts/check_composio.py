"""
scripts/check_composio.py
─────────────────────────
Preflight check for the Composio + Google Calendar integration used by Baymax's
appointment scheduling.

Run from the repo root:
    uv run python scripts/check_composio.py

It verifies that:
  1. COMPOSIO_API_KEY / COMPOSIO_USER_ID are set (.env).
  2. The Composio client initialises.
  3. A Google Calendar account is connected (and prints its id/status).
  4. The GOOGLECALENDAR_CREATE_EVENT action is reachable.

Nothing is created or modified — this is read-only.
"""

import os
import sys

from dotenv import load_dotenv

load_dotenv()


def main() -> int:
    api_key = os.environ.get("COMPOSIO_API_KEY")
    user_id = os.environ.get("COMPOSIO_USER_ID")

    if not api_key or not user_id:
        print("[FAIL] COMPOSIO_API_KEY / COMPOSIO_USER_ID missing from .env", file=sys.stderr)
        return 1

    try:
        from composio import Composio
    except Exception as e:  # pragma: no cover
        print(f"[FAIL] composio not installed: {e}", file=sys.stderr)
        return 1

    try:
        client = Composio(api_key=api_key)
        print("[ OK ] Composio client initialised")

        accounts = client.connected_accounts.list()
        items = getattr(accounts, "items", accounts)
        gcal = [a for a in items if "googlecalendar" in str(getattr(a, "toolkit", "")).lower()]
        if not gcal:
            print("[WARN] No Google Calendar account connected under this user_id.")
            print("       Connect one in the Composio dashboard, then re-run.")
            return 1
        for a in gcal:
            print(f"[ OK ] Google Calendar connected — status={getattr(a, 'status', '?')} "
                  f"id={getattr(a, 'id', '?')}")

        tools = client.tools.get(user_id=user_id, tools=["GOOGLECALENDAR_CREATE_EVENT"])
        if tools:
            print("[ OK ] GOOGLECALENDAR_CREATE_EVENT action is reachable")
        else:
            print("[WARN] GOOGLECALENDAR_CREATE_EVENT not returned — check toolkit access")
            return 1

        print("\n[DONE] Composio + Google Calendar look good.")
        return 0

    except Exception as e:
        print(f"[FAIL] Composio check failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

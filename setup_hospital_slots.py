"""
setup_hospital_slots.py
───────────────────────
Creates the hospital_slots table and seeds it with appointment slots
for the next 14 days.

Each day gets standard clinic hours:
  - Morning:   09:00, 09:30, 10:00, 10:30, 11:00, 11:30
  - Afternoon:  14:00, 14:30, 15:00, 15:30, 16:00, 16:30

All slots default to is_booked = false (available).
When a patient books, is_booked → true and booked_patient_id is set.
This prevents double-booking: P001 books a slot → P002 cannot book it.

Run:  uv run python setup_hospital_slots.py
"""

import os
import sys
import psycopg
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

DB_URI = os.environ.get("SUPABASE_DB_URI", "")
if not DB_URI:
    print("[ERROR] SUPABASE_DB_URI not set in .env", file=sys.stderr)
    sys.exit(1)

# ── Slot template: (hour, minute) ────────────────────────────────────────────
SLOT_TIMES = [
    (9, 0), (10, 0), (11, 0),
    (14, 0), (15, 0), (16, 0),
]

SEED_DAYS = 14  # Generate slots for the next 14 days
SLOT_DURATION = 60  # minutes


def main():
    conn = psycopg.connect(DB_URI)
    cur = conn.cursor()

    # ── Step 1: Create the table ──────────────────────────────────────────────
    print("[1/3] Creating hospital_slots table...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS hospital_slots (
            slot_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            slot_datetime     TIMESTAMPTZ NOT NULL,
            duration_minutes  INTEGER NOT NULL DEFAULT 30,
            is_booked         BOOLEAN NOT NULL DEFAULT false,
            booked_patient_id TEXT REFERENCES patients(patient_id) ON DELETE SET NULL,
            doctor_name       TEXT NOT NULL DEFAULT 'Dr. Amanda Ross',
            created_at        TIMESTAMPTZ DEFAULT NOW(),

            -- Prevent duplicate slots for the same datetime + doctor
            UNIQUE(slot_datetime, doctor_name)
        );
    """)

    # ── Step 2: Create index for fast lookups ────────────────────────────────
    print("[2/3] Creating indexes...")
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_slots_date_booked
        ON hospital_slots (slot_datetime, is_booked)
        WHERE is_booked = false;
    """)

    # ── Step 3: Seed slots for the next 14 days ──────────────────────────────
    print(f"[3/3] Seeding slots for the next {SEED_DAYS} days...")
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    inserted = 0
    skipped = 0

    for day_offset in range(SEED_DAYS):
        day = today + timedelta(days=day_offset)

        # Skip Sundays (weekday 6)
        if day.weekday() == 6:
            continue

        for hour, minute in SLOT_TIMES:
            slot_dt = day.replace(hour=hour, minute=minute)

            # Use ON CONFLICT to skip already-existing slots
            cur.execute("""
                INSERT INTO hospital_slots (slot_datetime, duration_minutes, doctor_name)
                VALUES (%s, %s, 'Dr. Amanda Ross')
                ON CONFLICT (slot_datetime, doctor_name) DO NOTHING;
            """, (slot_dt, SLOT_DURATION))

            if cur.rowcount > 0:
                inserted += 1
            else:
                skipped += 1

    conn.commit()

    # ── Verification ──────────────────────────────────────────────────────────
    cur.execute("SELECT COUNT(*) FROM hospital_slots")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM hospital_slots WHERE is_booked = false")
    available = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM hospital_slots WHERE is_booked = true")
    booked = cur.fetchone()[0]

    print(f"\n[OK] Done!")
    print(f"   Inserted: {inserted} new slots")
    print(f"   Skipped:  {skipped} (already existed)")
    print(f"   Total:    {total} slots in table")
    print(f"   Available: {available} | Booked: {booked}")

    # Show sample for today/tomorrow
    tomorrow = today + timedelta(days=1)
    cur.execute("""
        SELECT slot_datetime, duration_minutes, is_booked, doctor_name
        FROM hospital_slots
        WHERE DATE(slot_datetime) = %s
        ORDER BY slot_datetime
        LIMIT 5
    """, (tomorrow.date(),))
    rows = cur.fetchall()
    if rows:
        print(f"\n   Sample slots for {tomorrow.strftime('%Y-%m-%d')}:")
        for r in rows:
            status = "BOOKED" if r[2] else "OPEN"
            print(f"     {r[0].strftime('%I:%M %p')} ({r[1]} min) — {r[3]} [{status}]")

    conn.close()


if __name__ == "__main__":
    main()

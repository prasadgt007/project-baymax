-- ============================================================
-- Project Baymax — Hospital Slots Migration
-- Run in: Supabase Dashboard → SQL Editor → New Query
-- ============================================================

-- 1. Hospital appointment slots table
CREATE TABLE IF NOT EXISTS hospital_slots (
    slot_id               uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    slot_datetime         timestamp NOT NULL,         -- Local time (Asia/Kolkata / IST)
    duration_minutes      integer NOT NULL DEFAULT 60,
    is_booked             boolean NOT NULL DEFAULT false,
    booked_patient_id     text REFERENCES patients(patient_id) ON DELETE SET NULL
);

-- 2. Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_hospital_slots_date
    ON hospital_slots (DATE(slot_datetime));

CREATE INDEX IF NOT EXISTS idx_hospital_slots_booked
    ON hospital_slots (is_booked);

-- 3. Enable RLS (consistent with the rest of the schema)
ALTER TABLE hospital_slots ENABLE ROW LEVEL SECURITY;

-- 4. Seed mock appointment slots
--    7 days of slots: 09:00, 10:00, 11:00, 14:00, 15:00, 16:00
--    Mix: most are available, a few pre-booked for P001 as demo data.

INSERT INTO hospital_slots (slot_datetime, duration_minutes, is_booked, booked_patient_id) VALUES
-- 2026-07-01 (Wednesday)
('2026-07-01 09:00:00', 60, false, NULL),
('2026-07-01 10:00:00', 60, true,  'P001'),
('2026-07-01 11:00:00', 60, false, NULL),
('2026-07-01 14:00:00', 60, false, NULL),
('2026-07-01 15:00:00', 60, false, NULL),
('2026-07-01 16:00:00', 60, false, NULL),

-- 2026-07-02 (Thursday)
('2026-07-02 09:00:00', 60, false, NULL),
('2026-07-02 10:00:00', 60, false, NULL),
('2026-07-02 11:00:00', 60, true,  'P002'),
('2026-07-02 14:00:00', 60, false, NULL),
('2026-07-02 15:00:00', 60, false, NULL),
('2026-07-02 16:00:00', 60, false, NULL),

-- 2026-07-03 (Friday)
('2026-07-03 09:00:00', 60, false, NULL),
('2026-07-03 10:00:00', 60, false, NULL),
('2026-07-03 11:00:00', 60, false, NULL),
('2026-07-03 14:00:00', 60, false, NULL),
('2026-07-03 15:00:00', 60, false, NULL),
('2026-07-03 16:00:00', 60, false, NULL),

-- 2026-07-04 (Saturday — reduced schedule)
('2026-07-04 09:00:00', 60, false, NULL),
('2026-07-04 10:00:00', 60, false, NULL),
('2026-07-04 11:00:00', 60, false, NULL),

-- 2026-07-07 (Monday)
('2026-07-07 09:00:00', 60, false, NULL),
('2026-07-07 10:00:00', 60, false, NULL),
('2026-07-07 11:00:00', 60, false, NULL),
('2026-07-07 14:00:00', 60, false, NULL),
('2026-07-07 15:00:00', 60, false, NULL),
('2026-07-07 16:00:00', 60, false, NULL),

-- 2026-07-08 (Tuesday)
('2026-07-08 09:00:00', 60, false, NULL),
('2026-07-08 10:00:00', 60, false, NULL),
('2026-07-08 11:00:00', 60, false, NULL),
('2026-07-08 14:00:00', 60, false, NULL),
('2026-07-08 15:00:00', 60, false, NULL),
('2026-07-08 16:00:00', 60, false, NULL)

ON CONFLICT DO NOTHING;

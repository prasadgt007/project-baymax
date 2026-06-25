"""
test_supabase.py
────────────────
Verifies:
  1. SUPABASE_DB_URI is present and not a placeholder
  2. psycopg can connect to Supabase Postgres
  3. pgvector extension is enabled (vector type available)
  4. The 'patients' and 'patient_interactions' tables exist

Run with:
  uv run python test_supabase.py
"""
import os
import sys

from dotenv import load_dotenv
load_dotenv()

PLACEHOLDER = "YOUR_PROJECT_REF"


def check(label: str, passed: bool, detail: str = ""):
    icon = "OK  " if passed else "FAIL"
    msg = f"  [{icon}] {label}"
    if detail:
        msg += f" - {detail}"
    print(msg)
    return passed


def main():
    print("\n=== Supabase Connection Test ===\n")
    all_ok = True

    # ── 1. env var present ─────────────────────────────────────────────────
    db_uri = os.environ.get("SUPABASE_DB_URI", "")
    uri_ok = bool(db_uri) and PLACEHOLDER not in db_uri
    all_ok &= check(
        "SUPABASE_DB_URI loaded",
        uri_ok,
        "placeholder still present - update .env" if not uri_ok else db_uri[:60] + "...",
    )
    if not uri_ok:
        print("\n[ERROR] Fix SUPABASE_DB_URI in .env first, then re-run.\n")
        sys.exit(1)

    # ── 2. psycopg import ──────────────────────────────────────────────────
    try:
        import psycopg
        all_ok &= check("psycopg3 importable", True)
    except ImportError as e:
        check("psycopg3 importable", False, str(e))
        print("\n[ERROR] Run: uv pip install psycopg[binary] --link-mode=copy\n")
        sys.exit(1)

    # ── 3. TCP connection ──────────────────────────────────────────────────
    try:
        conn = psycopg.connect(db_uri)
        all_ok &= check("TCP connection to Supabase", True)
    except Exception as e:
        check("TCP connection to Supabase", False, str(e))
        print("\n[ERROR] Cannot connect. Check credentials / firewall.\n")
        sys.exit(1)

    with conn:
        cur = conn.cursor()

        # ── 4. pgvector extension ──────────────────────────────────────────
        cur.execute(
            "SELECT extname FROM pg_extension WHERE extname = 'vector';"
        )
        ext_row = cur.fetchone()
        all_ok &= check(
            "pgvector extension enabled",
            ext_row is not None,
            "run: CREATE EXTENSION IF NOT EXISTS vector;" if not ext_row else "ok",
        )

        # ── 5. tables exist ────────────────────────────────────────────────
        for table in ("patients", "patient_interactions"):
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = %s
                );
                """,
                (table,),
            )
            exists = cur.fetchone()[0]
            all_ok &= check(
                f"table '{table}' exists",
                exists,
                "missing — run supabase_schema.sql in the SQL Editor" if not exists else "",
            )

        # ── 6. quick row count ─────────────────────────────────────────────
        if all_ok:
            cur.execute("SELECT COUNT(*) FROM patients;")
            n = cur.fetchone()[0]
            check(f"patients row count", True, f"{n} rows")

            cur.execute("SELECT COUNT(*) FROM patient_interactions;")
            m = cur.fetchone()[0]
            check(f"patient_interactions row count", True, f"{m} rows")

    print()
    if all_ok:
        print("\n[SUCCESS] All checks passed - Supabase is connected and ready!\n")
    else:
        print("\n[FAILED] Some checks failed. Review the output above.\n")
        sys.exit(1)


if __name__ == "__main__":
    main()

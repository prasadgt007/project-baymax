"""
tools.py
────────
LangChain @tool-decorated functions for the Baymax DeepAgent.

These wrap the existing MCP client functions so that `create_deep_agent`
can call them as standard LangChain tools. The patient_id is injected
from the graph state via closure — the LLM never controls which patient's
data it accesses.

Tools:
  1. search_patient_records  — Merged semantic search (documents + interactions)
  2. get_patient_profile     — Fetch demographics, conditions, allergies, meds
  3. get_available_slots     — Query open appointment slots for a date
  4. book_appointment        — Book a specific slot for the current patient
  5. generate_doctor_brief   — Create a pre-consultation brief after booking
"""

import re
from typing import Optional
from langchain_core.tools import tool
from .mcp_client import (
    fetch_patient_profile_mcp,
    search_interactions_mcp,
    search_patient_documents_mcp,
    fetch_available_slots_mcp,
    book_slot_mcp,
    fetch_patient_appointments_mcp,
    cancel_slot_mcp,
    set_slot_calendar_event_mcp,
)
from .briefs import generate_pre_consultation_brief

_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def _time_hint_matches(label: str, hint: str) -> bool:
    """
    Return True if a free-text time hint (e.g. "3pm", "the 3 PM one", "15:00",
    "11 am") refers to the time in an appointment `label` such as
    "Thursday, July 16 at 03:00 PM".

    This lets cancellation/rescheduling work when the LLM passes a description
    instead of a real slot UUID — we resolve it from the patient's actual bookings.
    """
    if not label or not hint:
        return False
    label_l = label.lower()

    # 12-hour form: "3pm", "3 pm", "3:00 pm"
    m = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)", hint.lower())
    if m:
        hour = int(m.group(1))
        meridiem = "pm" if m.group(3).startswith("p") else "am"
        hour12 = 12 if hour % 12 == 0 else hour % 12
        return f"{hour12:02d}:" in label_l and meridiem in label_l

    # 24-hour form: "15:00", "15"
    m = re.search(r"\b([01]?\d|2[0-3]):?([0-5]\d)?\b", hint)
    if m:
        hour = int(m.group(1))
        meridiem = "pm" if hour >= 12 else "am"
        hour12 = 12 if hour % 12 == 0 else hour % 12
        return f"{hour12:02d}:" in label_l and meridiem in label_l

    return False


def create_baymax_tools(patient_id: str):
    """
    Factory that creates a set of LangChain tools bound to a specific patient_id.
    This prevents the LLM from accessing another patient's data.
    """

    @tool
    def search_patient_records(query: str) -> str:
        """
        Search the patient's medical records using semantic similarity.
        Searches both uploaded documents (blood tests, x-rays, reports, prescriptions)
        and historical visit interaction notes.
        Use this tool whenever you need to look up specific medical data, lab values,
        past diagnoses, or any information from the patient's medical history.

        Args:
            query: The search query describing what to look for
                   (e.g. "cholesterol levels", "blood pressure", "migraine history")
        """
        results = []

        # Search uploaded documents (typed: reports, x-rays, blood tests, prescriptions)
        try:
            doc_results = search_patient_documents_mcp(patient_id, query=query, limit=3)
            for doc in doc_results:
                doc_type = doc.get("document_type", "document")
                date = doc.get("created_at", "Unknown date")
                content = doc.get("content_text", "")
                results.append(f"[{doc_type}] ({date}):\n{content}")
        except Exception as e:
            results.append(f"[Document search error: {e}]")

        # Search historical interaction notes
        try:
            interaction_results = search_interactions_mcp(patient_id, query=query, limit=3)
            for inter in interaction_results:
                date = inter.get("date", "Unknown date")
                notes = inter.get("notes", "")
                results.append(f"[visit_notes] ({date}):\n{notes}")
        except Exception as e:
            results.append(f"[Interaction search error: {e}]")

        if not results:
            return "No matching records found for this patient."

        return "\n\n---\n\n".join(results)

    @tool
    def get_patient_profile() -> str:
        """
        Fetch the patient's full profile including demographics, past conditions,
        allergies, and current medications.
        Use this when you need to check for allergies before recommending remedies,
        or to reference the patient's medical history.
        """
        try:
            profile = fetch_patient_profile_mcp(patient_id)
            if not profile:
                return "Patient profile not found in the database."

            return (
                f"Name: {profile.name}\n"
                f"Age: {profile.age}\n"
                f"Past Conditions: {', '.join(profile.history.past_conditions) or 'None'}\n"
                f"Allergies: {', '.join(profile.history.allergies) or 'None'}\n"
                f"Current Medications: {', '.join(profile.history.current_medications) or 'None'}\n"
                f"Past Interactions: {len(profile.past_interactions)} on record"
            )
        except Exception as e:
            return f"Error fetching profile: {e}"

    @tool
    def get_available_slots(date: str = "", number_of_days: int = 7) -> str:
        """
        Get available (unbooked) appointment slots.
        - If 'date' is provided (YYYY-MM-DD), returns slots for that specific date only.
        - If 'date' is empty (default), returns all available slots for the next 'number_of_days' days.
        Use this when the patient wants to schedule an appointment. Call it WITHOUT a date
        first so the patient can see all upcoming options and pick one.

        Args:
            date: Optional. Specific date in YYYY-MM-DD format. Leave empty for upcoming slots.
            number_of_days: How many days ahead to search (1-14). Defaults to 7.
        """
        try:
            slots = fetch_available_slots_mcp(date_str=date, number_of_days=number_of_days)
            if not slots:
                if date:
                    return f"No available slots found for {date}. Try a different date or leave the date empty to see all upcoming availability."
                return f"No available slots found in the next {number_of_days} days. Try increasing the range."

            # Group by date for readability
            from collections import defaultdict
            by_day = defaultdict(list)
            for s in slots:
                day_label = s["slot_datetime"][:10]  # YYYY-MM-DD
                by_day[day_label].append(s)

            # If no date was specified, only show the first available day (next working day)
            if not date:
                first_available_day = list(by_day.keys())[0]
                by_day = {first_available_day: by_day[first_available_day]}

            lines = ["Here are the available appointment slots:"]
            slot_num = 1
            for day, day_slots in by_day.items():
                day_header = day_slots[0]['label'].split(' at ')[0] if ' at ' in day_slots[0]['label'] else day
                lines.append(f"\n**{day_header}:**")
                for s in day_slots:
                    time_part = s['label'].split(' at ')[-1] if ' at ' in s['label'] else s['label']
                    lines.append(f"  {slot_num}. {time_part}")
                    lines.append(f"     slot_id: {s['slot_id']}")
                    slot_num += 1

            lines.append("\nIMPORTANT: To book, you MUST use the slot_id (the UUID value), NOT the time label.")
            lines.append("Ask the patient which time they prefer, then call book_appointment with the corresponding slot_id UUID.")
            return "\n".join(lines)
        except Exception as e:
            return f"Error fetching slots: {e}"

    @tool
    def book_appointment(slot_id: str) -> str:
        """
        Book a specific appointment slot for the current patient.
        CRITICAL: The slot_id MUST be a UUID string from the get_available_slots output.
        Example valid slot_id: "c5b1b270-853f-4cb8-b38b-08cb65253ae4"
        NEVER pass a date/time string like "Tuesday, July 14 at 10:30 AM" as slot_id.

        Args:
            slot_id: The UUID of the slot to book. Must look like "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx".
        """
        try:
            result = book_slot_mcp(slot_id, patient_id)
            if not result.get("success"):
                return f"❌ Booking failed: {result.get('error', 'Slot may already be taken.')}"

            label = result.get("label", "your appointment")
            doctor = result.get("doctor_name") or "the doctor"

            # ── Best-effort: create a Google Calendar event via Composio ──────────
            # A failure here must NOT break the booking — the slot is already
            # reserved in the database. We only note the calendar outcome.
            calendar_note = ""
            try:
                from .calendar_client import create_appointment_event

                # Resolve patient name for a friendlier event title (best-effort)
                patient_name = patient_id
                try:
                    profile = fetch_patient_profile_mcp(patient_id)
                    if profile and getattr(profile, "name", None):
                        patient_name = profile.name
                except Exception:
                    pass

                cal = create_appointment_event(
                    start_datetime=result.get("slot_datetime", ""),
                    duration_minutes=result.get("duration_minutes", 60),
                    summary=f"Doctor Appointment — {patient_name} with {doctor}",
                    description=(
                        f"Baymax-scheduled appointment.\n"
                        f"Patient: {patient_name} ({patient_id})\n"
                        f"Doctor: {doctor}\n"
                        f"When: {label}"
                    ),
                )
                if cal.get("success"):
                    calendar_note = " It has also been added to the Google Calendar."
                    # Persist the event_id so we can delete it on cancel/reschedule.
                    event_id = cal.get("event_id")
                    if event_id:
                        try:
                            set_slot_calendar_event_mcp(slot_id, event_id)
                        except Exception as e:
                            print(f"[book_appointment] Could not persist calendar event_id: {e}")
                else:
                    calendar_note = ""  # stay silent to the patient on calendar failure
                    print(f"[book_appointment] Calendar event failed: {cal.get('error')}")
            except Exception as e:
                print(f"[book_appointment] Calendar integration error: {e}")

            return f"✅ Appointment booked successfully for {label} with {doctor}.{calendar_note}"
        except Exception as e:
            return f"Error booking appointment: {e}"

    @tool
    def get_my_appointments() -> str:
        """
        Get all upcoming booked appointments for the current patient.
        Use this when the patient asks about their existing appointments,
        wants to reschedule, or wants to cancel.
        Returns a list of booked appointments with dates, times, and doctor names.
        """
        try:
            appointments = fetch_patient_appointments_mcp(patient_id)
            if not appointments:
                return "You have no upcoming appointments."

            lines = ["Your upcoming appointments:"]
            for i, appt in enumerate(appointments, 1):
                doctor = appt.get('doctor_name', 'Dr. Amanda Ross')
                lines.append(f"  {i}. {appt['label']} with {doctor} (ID: {appt['slot_id']})")
            return "\n".join(lines)
        except Exception as e:
            return f"Error fetching appointments: {e}"

    @tool
    def cancel_appointment(slot_id: str = "", appointment_time: str = "") -> str:
        """
        Cancel an existing appointment for the current patient. The slot becomes
        available again for other patients. Use this to cancel, or as step 1 of a reschedule.

        You can identify the appointment in any of these ways:
          - `slot_id`: the exact UUID from get_my_appointments (most precise), OR
          - `appointment_time`: a natural time description such as "3pm", "03:00 PM",
            or "11 am" — the tool will match it against the patient's real bookings.
        If the patient has only one upcoming appointment, both arguments may be empty.

        Args:
            slot_id: The appointment slot UUID, if known.
            appointment_time: A time/label describing which appointment to cancel.
        """
        try:
            appointments = fetch_patient_appointments_mcp(patient_id)
            if not appointments:
                return "You have no upcoming appointments to cancel."

            target = None

            # 1) Exact UUID match (preferred)
            sid = (slot_id or "").strip()
            if _UUID_RE.match(sid):
                target = next((a for a in appointments if a.get("slot_id") == sid), None)

            # 2) Resolve from a time hint — searches BOTH provided fields, so even a
            #    placeholder like "the slot_id of the 3pm appointment" still resolves.
            if target is None:
                hint = f"{appointment_time or ''} {slot_id or ''}".strip()
                matches = [a for a in appointments if _time_hint_matches(a.get("label", ""), hint)]
                if len(matches) == 1:
                    target = matches[0]
                elif len(matches) > 1:
                    lines = ["You have more than one appointment at that time — which one?"]
                    for i, a in enumerate(appointments, 1):
                        lines.append(f"  {i}. {a['label']}")
                    return "\n".join(lines)

            # 3) Single-appointment fallback
            if target is None and len(appointments) == 1:
                target = appointments[0]

            if target is None:
                lines = ["I couldn't tell which appointment you mean. You currently have:"]
                for i, a in enumerate(appointments, 1):
                    lines.append(f"  {i}. {a['label']}")
                lines.append("Which one would you like to cancel?")
                return "\n".join(lines)

            result = cancel_slot_mcp(target["slot_id"], patient_id)
            if result.get("success"):
                # Best-effort: remove the matching Google Calendar event so the
                # calendar stays in sync (important for reschedules).
                event_id = result.get("calendar_event_id")
                if event_id:
                    try:
                        from .calendar_client import delete_calendar_event
                        cal = delete_calendar_event(event_id)
                        if not cal.get("success"):
                            print(f"[cancel_appointment] Calendar delete failed: {cal.get('error')}")
                    except Exception as e:
                        print(f"[cancel_appointment] Calendar delete error: {e}")
                return (
                    f"The appointment on {target['label']} has been successfully cancelled. "
                    f"The slot is now available for others."
                )
            return f"Could not cancel appointment: {result.get('error', 'Appointment not found.')}"
        except Exception as e:
            return f"Error cancelling appointment: {e}"

    @tool
    def generate_brief_for_doctor(symptoms_summary: str = "") -> str:
        """
        Generate a pre-consultation brief for the attending doctor.
        Call this AFTER successfully booking an appointment.
        The brief summarises the patient's profile and relevant medical history,
        including the scheduled appointment date/time.

        Args:
            symptoms_summary: A short, plain-language summary of the symptoms and
                triage details discussed with the patient THIS session (e.g.
                "Dull headache, 5/10, both sides, 2 days, no fever"). Leave EMPTY
                if the patient only booked an appointment without discussing symptoms —
                in that case a lighter history-only summary is produced automatically.

        NOTE: This brief is for hospital staff only. Never repeat its contents back
        to the patient — just confirm the appointment to them.
        """
        try:
            # Fetch the patient's next appointment to include in the brief
            appointment_label = ""
            try:
                appointments = fetch_patient_appointments_mcp(patient_id)
                if appointments:
                    next_appt = appointments[0]
                    doctor = next_appt.get("doctor_name", "")
                    appointment_label = next_appt.get("label", "")
                    if doctor:
                        appointment_label += f" with {doctor}"
            except Exception:
                pass

            brief = generate_pre_consultation_brief(
                patient_id=patient_id,
                current_symptoms=[],
                risk_flag=False,
                escalation_reason="",
                clinical_context=[],
                appointment_datetime=appointment_label,
                symptoms_summary=symptoms_summary or "",
            )
            return brief
        except Exception as e:
            return f"Error generating brief: {e}"

    return [
        search_patient_records,
        get_patient_profile,
        get_available_slots,
        book_appointment,
        get_my_appointments,
        cancel_appointment,
        generate_brief_for_doctor,
    ]

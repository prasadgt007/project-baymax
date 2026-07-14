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
)
from .briefs import generate_pre_consultation_brief


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
            if result.get("success"):
                return f"✅ Appointment booked successfully! Slot ID: {slot_id}"
            else:
                return f"❌ Booking failed: {result.get('error', 'Slot may already be taken.')}"
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
    def cancel_appointment(slot_id: str) -> str:
        """
        Cancel an existing appointment for the current patient.
        The slot becomes available again for other patients to book.
        Use this when the patient wants to cancel or as the first step of rescheduling.

        Args:
            slot_id: The UUID of the appointment slot to cancel (from get_my_appointments output)
        """
        try:
            result = cancel_slot_mcp(slot_id, patient_id)
            if result.get("success"):
                return f"Appointment (Slot ID: {slot_id}) has been successfully cancelled. The slot is now available for others."
            else:
                return f"Could not cancel appointment: {result.get('error', 'Appointment not found or does not belong to you.')}"
        except Exception as e:
            return f"Error cancelling appointment: {e}"

    @tool
    def generate_brief_for_doctor() -> str:
        """
        Generate a pre-consultation brief for the attending doctor.
        Call this AFTER successfully booking an appointment.
        The brief summarises the patient's profile, current symptoms discussed,
        and relevant medical history, including the scheduled appointment date/time.
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

"""
briefs.py
─────────
Generates a Markdown pre-consultation brief for the doctor.

Called after appointment confirmation in scheduling_agent.
Only surfaced to hospital_employee sessions by the server layer.
"""

from typing import List
from .mcp_client import fetch_patient_profile_mcp
from .models import Symptom


def generate_pre_consultation_brief(
    patient_id: str,
    current_symptoms: List[Symptom],
    risk_flag: bool,
    escalation_reason: str,
    clinical_context: List[dict] = None,
    appointment_datetime: str = "",
    symptoms_summary: str = "",
) -> str:
    """
    Synthesises patient profile, current triage findings, and semantically
    retrieved past visits into a Markdown brief for the attending physician.

    Uses blockquotes and lists instead of tables for clean frontend rendering.

    Args:
        patient_id:           Patient identifier used to fetch the DB profile.
        current_symptoms:     Structured symptoms extracted during this session.
        risk_flag:            True if the risk agent flagged this as high-priority.
        escalation_reason:    Human-readable reason string when risk_flag is True.
        clinical_context:     Relevant past interactions from pgvector search.
        appointment_datetime: Human-readable appointment date/time string.

    Returns:
        A Markdown string. Returns an error note if the profile is not found.
    """
    if clinical_context is None:
        clinical_context = []

    # A brief is a full "Pre-Consultation Brief" only when symptoms were actually
    # discussed this session. If the patient just booked an appointment without any
    # triage, we produce a lighter history-only "Patient Summary" instead.
    has_symptoms = bool((symptoms_summary or "").strip() or current_symptoms)
    title = "Pre-Consultation Brief" if has_symptoms else "Patient Summary"

    profile = fetch_patient_profile_mcp(patient_id)
    if not profile:
        return (
            f"## {title}\n\n"
            f"> Patient `{patient_id}` not found in the database.\n"
        )

    # ── Patient Identity Card ─────────────────────────────────────────────────
    lines = [
        f"## {title}",
        "",
        "### Patient Information",
        "",
        f"- **Name:** {profile.name}",
        f"- **Patient ID:** `{profile.patient_id}`",
        f"- **Age:** {profile.age} years",
    ]

    if appointment_datetime:
        lines.append(f"- **Scheduled Appointment:** {appointment_datetime}")

    # ── Medical History ───────────────────────────────────────────────────────
    lines += [
        "",
        "---",
        "",
        "### Medical History",
        "",
        f"- **Past Conditions:** {', '.join(profile.history.past_conditions) or 'None on record'}",
        f"- **Allergies:** {', '.join(profile.history.allergies) or 'None known'}",
        f"- **Current Medications:** {', '.join(profile.history.current_medications) or 'None'}",
        "",
    ]

    # ── Reason for Visit / Symptoms discussed this session ────────────────────
    if symptoms_summary and symptoms_summary.strip():
        lines += [
            "---",
            "",
            "### Reason for Visit / Symptoms Discussed",
            "",
            symptoms_summary.strip(),
            "",
        ]

    # ── Current Symptoms (structured, if available) ───────────────────────────
    if current_symptoms:
        lines += [
            "---",
            "",
            "### Current Presenting Symptoms",
            "",
        ]
        for s in current_symptoms:
            sdict = s.model_dump() if hasattr(s, "model_dump") else (s.dict() if hasattr(s, "dict") else s)
            lines.append(
                f"- **{sdict.get('name', 'Unknown')}** — "
                f"Severity: *{sdict.get('severity', '?')}*, "
                f"Duration: *{sdict.get('duration', '?')}*"
            )
        lines.append("")

    # ── Relevant Past Interactions ────────────────────────────────────────────
    if clinical_context:
        lines += [
            "---",
            "",
            "### Relevant Past Interactions",
            "",
        ]
        for entry in clinical_context:
            lines.append(
                f"- **{entry.get('date', 'Unknown date')}:** {entry.get('notes', '')}"
            )
        lines.append("")

    # ── Risk Assessment (only meaningful when triage actually happened) ────────
    if has_symptoms:
        lines += [
            "---",
            "",
            "### Risk Assessment",
            "",
        ]
        if risk_flag:
            lines += [
                "> **HIGH RISK DETECTED**",
                ">",
                f"> {escalation_reason or 'Immediate medical attention recommended.'}",
            ]
        else:
            lines.append("> **SAFE** — No immediate red flags detected during triage.")
    else:
        lines += [
            "---",
            "",
            "### Note",
            "",
            "> No symptoms were discussed this session — this is a history summary for the "
            "upcoming appointment.",
        ]

    # ── Footer ────────────────────────────────────────────────────────────────
    lines += [
        "",
        "---",
        "",
        "*Generated by Baymax AI — Confidential — For Authorised Medical Staff Only*",
    ]

    return "\n".join(lines)

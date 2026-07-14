/**
 * api.js
 * ──────
 * API service for communicating with the Project Baymax FastAPI backend.
 *
 * Uses relative URLs (/api/...) proxied through Vite's dev server to
 * FastAPI on port 8000. This means the same code works locally AND
 * through any ngrok / tunnel URL shared with teammates.
 */

const API_BASE = '/api'

// ── Session Initialization ───────────────────────────────────────────────────

/**
 * Initialize a patient session — proactive context loading at login.
 * Fetches baseline data (profile, documents, upcoming slot) and generates
 * a personalised greeting.
 *
 * @param {string} patientId - Patient identifier (e.g. 'P001').
 * @param {string} userRole  - 'patient' | 'hospital_employee'
 * @returns {Promise<{patient_name, age, chronic_conditions, allergies, medications, baseline_documents, upcoming_slot, greeting}>}
 */
export async function initializeSession(patientId, userRole = 'patient') {
  const res = await fetch(`${API_BASE}/initialize_session`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      patient_id: patientId,
      user_role: userRole,
    }),
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `Server error (${res.status})`)
  }
  return res.json()
}

// ── Chat ─────────────────────────────────────────────────────────────────────

/**
 * Send a chat message to the multi-agent graph.
 *
 * @param {string} userMessage  - The patient's message text.
 * @param {string} patientId    - Patient identifier (e.g. 'P001').
 * @param {string} userRole     - 'patient' | 'hospital_employee'
 * @returns {Promise<{response, intent, risk_flag, available_slots, doctor_brief}>}
 */
export async function sendMessage(userMessage, patientId, userRole = 'patient') {
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_message: userMessage,
      patient_id: patientId,
      user_role: userRole,
    }),
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `Server error (${res.status})`)
  }
  return res.json()
}

// ── Document Ingestion (hospital employees only) ──────────────────────────────

/**
 * Upload a PDF file and ingest it into the patient's vector store.
 * The server will reject this with HTTP 403 if user_role != 'hospital_employee'.
 *
 * @param {string} patientId    - Patient ID to associate the document with.
 * @param {string} userRole     - Must be 'hospital_employee'.
 * @param {File}   file         - A File object (PDF) from an <input type="file">.
 * @param {string} documentType - One of: 'report', 'xray', 'blood_test', 'prescription'.
 * @returns {Promise<{success, patient_id, document_type, chars_ingested, message}>}
 */
export async function ingestDocument(patientId, userRole, file, documentType = 'report') {
  const formData = new FormData()
  formData.append('patient_id', patientId)
  formData.append('user_role', userRole)
  formData.append('document_type', documentType)
  formData.append('file', file)

  // Do NOT set Content-Type header manually — browser must set it with the
  // multipart boundary automatically when using FormData.
  const res = await fetch(`${API_BASE}/ingest`, {
    method: 'POST',
    body: formData,
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `Server error (${res.status})`)
  }
  return res.json()
}

// ── Pre-Consultation Brief (hospital employees only) ──────────────────────────

/**
 * Fetch a pre-consultation brief for a specific patient.
 * Returns HTTP 403 if called without hospital_employee role.
 *
 * @param {string} patientId - Patient identifier.
 * @returns {Promise<{patient_id, brief}>}
 */
export async function fetchBrief(patientId) {
  const res = await fetch(
    `${API_BASE}/brief/${encodeURIComponent(patientId)}?user_role=hospital_employee`
  )

  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `Server error (${res.status})`)
  }
  return res.json()
}

// ── Health Check ─────────────────────────────────────────────────────────────

export async function checkHealth() {
  const res = await fetch(`${API_BASE}/health`)
  return res.json()
}

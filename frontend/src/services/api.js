/**
 * API service for communicating with the Project Baymax FastAPI backend.
 *
 * Uses relative URLs (/api/...) so requests are proxied through Vite's
 * dev server — this means the same code works locally AND through any
 * ngrok / tunnel URL shared with teammates, with zero configuration.
 *
 * Endpoint:
 *   POST /api/chat
 *   Body: { "user_message": "...", "patient_id": "P001" }
 *   Response: { "response": "...", "intent": "...", "risk_flag": bool, "doctor_brief": "..." }
 */

/**
 * Send a message to the Baymax AI backend.
 *
 * @param {string} userMessage - The user's message text
 * @param {string} patientId - The patient identifier (e.g., "P001")
 * @returns {Promise<{response: string, intent?: string, risk_flag?: boolean, doctor_brief?: string}>}
 */
export async function sendMessage(userMessage, patientId) {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_message: userMessage,
      patient_id: patientId,
    }),
  })

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}))
    throw new Error(errorBody.detail || `Server error (${res.status})`)
  }

  const data = await res.json()
  return data
}

/**
 * Health check — verify the backend is reachable.
 * @returns {Promise<boolean>}
 */
export async function checkHealth() {
  try {
    const res = await fetch('/api/health', { signal: AbortSignal.timeout(3000) })
    return res.ok
  } catch {
    return false
  }
}


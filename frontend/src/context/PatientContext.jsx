import { createContext, useContext, useState, useCallback } from 'react'

const PatientContext = createContext(null)

export function PatientProvider({ children }) {
  const [patientId, setPatientId] = useState(null)

  const login = useCallback((id) => {
    setPatientId(id.trim().toUpperCase())
  }, [])

  const logout = useCallback(() => {
    setPatientId(null)
  }, [])

  return (
    <PatientContext.Provider value={{ patientId, login, logout }}>
      {children}
    </PatientContext.Provider>
  )
}

export function usePatient() {
  const context = useContext(PatientContext)
  if (!context) {
    throw new Error('usePatient must be used within a PatientProvider')
  }
  return context
}

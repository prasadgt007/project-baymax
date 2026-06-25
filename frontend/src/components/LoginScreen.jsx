import { useState } from 'react'
import { usePatient } from '../context/PatientContext'
import BaymaxLogo from './BaymaxLogo'

export default function LoginScreen() {
  const { login } = usePatient()
  const [inputValue, setInputValue] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = (e) => {
    e.preventDefault()
    const value = inputValue.trim()

    if (!value) {
      setError('Please enter a Patient ID')
      return
    }

    // Basic validation: should start with P followed by digits
    if (!/^P\d+$/i.test(value)) {
      setError('Patient ID should be in format: P001, P002, etc.')
      return
    }

    setError('')
    setIsLoading(true)

    // Small delay for polish
    setTimeout(() => {
      login(value)
    }, 600)
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      {/* Background decorative elements */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-96 h-96 bg-baymax-200/30 rounded-full blur-3xl" />
        <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-baymax-100/40 rounded-full blur-3xl" />
        <div className="absolute top-1/3 left-1/4 w-64 h-64 bg-baymax-300/10 rounded-full blur-2xl" />
      </div>

      <div className="animate-slide-up relative w-full max-w-md">
        {/* Glassmorphic Card */}
        <div className="relative bg-white/80 backdrop-blur-xl rounded-3xl shadow-2xl shadow-baymax-200/50 border border-white/60 p-8 sm:p-10">
          {/* Logo & Title */}
          <div className="flex flex-col items-center mb-8">
            <div className="animate-float mb-4">
              <BaymaxLogo size={72} />
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold text-surface-800 tracking-tight">
              Project Baymax
            </h1>
            <p className="text-surface-500 mt-2 text-center text-sm sm:text-base leading-relaxed">
              Your AI Healthcare Companion
            </p>
            <div className="w-12 h-1 bg-gradient-to-r from-baymax-400 to-baymax-600 rounded-full mt-4" />
          </div>

          {/* Login Form */}
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label
                htmlFor="patient-id-input"
                className="block text-sm font-medium text-surface-700 mb-2"
              >
                Enter Patient ID
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                  <svg className="w-5 h-5 text-surface-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z" />
                  </svg>
                </div>
                <input
                  id="patient-id-input"
                  type="text"
                  value={inputValue}
                  onChange={(e) => {
                    setInputValue(e.target.value)
                    if (error) setError('')
                  }}
                  placeholder="e.g., P001, P002"
                  className={`w-full pl-12 pr-4 py-3.5 rounded-xl border-2 bg-white/90 text-surface-800 placeholder:text-surface-400 text-sm
                    transition-all duration-200 outline-none
                    ${error
                      ? 'border-accent-danger/50 focus:border-accent-danger focus:ring-4 focus:ring-accent-danger/10'
                      : 'border-surface-200 focus:border-baymax-400 focus:ring-4 focus:ring-baymax-100'
                    }`}
                  autoComplete="off"
                  autoFocus
                />
              </div>
              {error && (
                <p className="mt-2 text-xs text-accent-danger flex items-center gap-1 animate-fade-in">
                  <svg className="w-3.5 h-3.5 shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z" clipRule="evenodd" />
                  </svg>
                  {error}
                </p>
              )}
            </div>

            <button
              id="start-demo-button"
              type="submit"
              disabled={isLoading}
              className="w-full py-3.5 px-6 rounded-xl font-semibold text-sm text-white
                bg-gradient-to-r from-baymax-500 to-baymax-600
                hover:from-baymax-600 hover:to-baymax-700
                active:from-baymax-700 active:to-baymax-800
                shadow-lg shadow-baymax-500/25 hover:shadow-xl hover:shadow-baymax-500/30
                transition-all duration-200
                disabled:opacity-60 disabled:cursor-not-allowed disabled:hover:shadow-lg
                cursor-pointer flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <>
                  <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" className="opacity-25" />
                    <path d="M4 12a8 8 0 018-8" stroke="currentColor" strokeWidth="3" strokeLinecap="round" className="opacity-75" />
                  </svg>
                  Connecting...
                </>
              ) : (
                <>
                  Start Demo
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
                  </svg>
                </>
              )}
            </button>
          </form>

          {/* Footer hint */}
          <p className="text-center text-xs text-surface-400 mt-6">
            Demo mode — enter any valid Patient ID to begin
          </p>
        </div>
      </div>
    </div>
  )
}

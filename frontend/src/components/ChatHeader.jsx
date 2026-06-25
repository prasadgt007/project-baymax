import { usePatient } from '../context/PatientContext'
import BaymaxLogo from './BaymaxLogo'

export default function ChatHeader() {
  const { patientId, logout } = usePatient()

  return (
    <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-xl border-b border-surface-200/60 shadow-sm">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        {/* Left — Brand */}
        <div className="flex items-center gap-3">
          <BaymaxLogo size={32} />
          <div>
            <h1 className="text-base font-bold text-surface-800 leading-tight">
              Project Baymax
            </h1>
            <p className="text-[11px] text-surface-400 -mt-0.5 hidden sm:block">
              AI Healthcare Companion
            </p>
          </div>
        </div>

        {/* Right — Patient info & Logout */}
        <div className="flex items-center gap-3">
          {/* Patient badge */}
          <div className="flex items-center gap-2 bg-baymax-50 border border-baymax-200/60 rounded-full px-3.5 py-1.5">
            <div className="w-2 h-2 rounded-full bg-accent-success animate-pulse" />
            <span className="text-xs font-medium text-baymax-700">
              <span className="hidden sm:inline">Active Patient: </span>
              {patientId}
            </span>
          </div>

          {/* Logout */}
          <button
            id="logout-button"
            onClick={logout}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium
              text-surface-500 hover:text-accent-danger hover:bg-accent-danger/5
              border border-transparent hover:border-accent-danger/20
              transition-all duration-200 cursor-pointer"
            title="End session"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0 0 13.5 3h-6a2.25 2.25 0 0 0-2.25 2.25v13.5A2.25 2.25 0 0 0 7.5 21h6a2.25 2.25 0 0 0 2.25-2.25V15m3 0 3-3m0 0-3-3m3 3H9" />
            </svg>
            <span className="hidden sm:inline">Logout</span>
          </button>
        </div>
      </div>
    </header>
  )
}

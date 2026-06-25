export default function TypingIndicator() {
  return (
    <div className="flex items-start gap-3 animate-fade-in-up">
      {/* Avatar */}
      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-baymax-400 to-baymax-600 flex items-center justify-center shadow-md shadow-baymax-300/30 shrink-0">
        <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09Z" />
        </svg>
      </div>

      {/* Bubble */}
      <div className="bg-white/90 backdrop-blur-sm border border-surface-200/80 rounded-2xl rounded-tl-md px-5 py-3.5 shadow-sm">
        <div className="flex items-center gap-1.5">
          <span className="typing-dot w-2 h-2 bg-baymax-400 rounded-full inline-block" />
          <span className="typing-dot w-2 h-2 bg-baymax-400 rounded-full inline-block" />
          <span className="typing-dot w-2 h-2 bg-baymax-400 rounded-full inline-block" />
        </div>
      </div>
    </div>
  )
}

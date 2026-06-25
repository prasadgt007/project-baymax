import { useState, useRef } from 'react'

export default function ChatInput({ onSend, disabled }) {
  const [message, setMessage] = useState('')
  const textareaRef = useRef(null)

  const handleSubmit = (e) => {
    e.preventDefault()
    const trimmed = message.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setMessage('')
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const handleInput = (e) => {
    setMessage(e.target.value)
    // Auto-resize textarea
    const el = e.target
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 120) + 'px'
  }

  return (
    <div className="sticky bottom-0 z-40 bg-gradient-to-t from-white via-white/95 to-white/0 pt-4 pb-4 px-4 sm:px-6">
      <form
        onSubmit={handleSubmit}
        className="max-w-4xl mx-auto flex items-end gap-3 bg-white/90 backdrop-blur-xl border border-surface-200/80 rounded-2xl px-4 py-3 shadow-lg shadow-surface-200/30"
      >
        <textarea
          id="chat-message-input"
          ref={textareaRef}
          value={message}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder="Describe your symptoms or ask a question..."
          disabled={disabled}
          rows={1}
          className="flex-1 resize-none bg-transparent text-sm text-surface-800 placeholder:text-surface-400
            outline-none py-1 max-h-[120px] leading-relaxed disabled:opacity-50"
        />

        <button
          id="send-message-button"
          type="submit"
          disabled={!message.trim() || disabled}
          className="shrink-0 w-10 h-10 rounded-xl flex items-center justify-center
            bg-gradient-to-r from-baymax-500 to-baymax-600
            hover:from-baymax-600 hover:to-baymax-700
            active:scale-95
            shadow-md shadow-baymax-500/20
            transition-all duration-200
            disabled:opacity-40 disabled:cursor-not-allowed disabled:active:scale-100
            cursor-pointer"
          title="Send message"
        >
          <svg className="w-4.5 h-4.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 12 3.269 3.125A59.769 59.769 0 0 1 21.485 12 59.768 59.768 0 0 1 3.27 20.875L5.999 12Zm0 0h7.5" />
          </svg>
        </button>
      </form>

      <p className="text-center text-[10px] text-surface-400 mt-2 max-w-4xl mx-auto">
        Baymax provides general health guidance — always consult a healthcare professional for medical decisions.
      </p>
    </div>
  )
}

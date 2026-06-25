import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

export default function ChatBubble({ message }) {
  const isUser = message.role === 'user'

  return (
    <div
      className={`flex items-start gap-3 animate-fade-in-up ${isUser ? 'flex-row-reverse' : ''}`}
    >
      {/* Avatar */}
      <div
        className={`w-8 h-8 rounded-full flex items-center justify-center shadow-md shrink-0
          ${isUser
            ? 'bg-gradient-to-br from-surface-500 to-surface-700 shadow-surface-300/30'
            : 'bg-gradient-to-br from-baymax-400 to-baymax-600 shadow-baymax-300/30'
          }`}
      >
        {isUser ? (
          <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z" />
          </svg>
        ) : (
          <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09Z" />
          </svg>
        )}
      </div>

      {/* Bubble */}
      <div
        className={`max-w-[80%] sm:max-w-[70%] rounded-2xl px-4 py-3 shadow-sm
          ${isUser
            ? 'bg-gradient-to-br from-baymax-500 to-baymax-600 text-white rounded-tr-md'
            : 'bg-white/90 backdrop-blur-sm border border-surface-200/80 text-surface-700 rounded-tl-md'
          }`}
      >
        {isUser ? (
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
        ) : (
          <>
            {message.riskFlag && (
              <div className="flex items-center gap-1.5 mb-2 px-2.5 py-1 bg-accent-danger/10 border border-accent-danger/20 rounded-lg text-accent-danger text-xs font-medium animate-fade-in">
                <svg className="w-3.5 h-3.5 shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
                </svg>
                High Risk Detected — Immediate attention recommended
              </div>
            )}
            <div className="markdown-content text-sm">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
            </div>
          </>
        )}

        {/* Timestamp */}
        <p
          className={`text-[10px] mt-2 ${isUser ? 'text-baymax-200' : 'text-surface-400'}`}
        >
          {message.timestamp}
        </p>
      </div>
    </div>
  )
}

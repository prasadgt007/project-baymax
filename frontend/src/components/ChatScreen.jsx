import { useState, useRef, useEffect, useCallback } from 'react'
import { usePatient } from '../context/PatientContext'
import { sendMessage } from '../services/api'
import ChatHeader from './ChatHeader'
import ChatInput from './ChatInput'
import ChatBubble from './ChatBubble'
import TypingIndicator from './TypingIndicator'
import BaymaxLogo from './BaymaxLogo'

function formatTime() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

const WELCOME_MESSAGE = {
  id: 'welcome',
  role: 'assistant',
  content: `Hello! 👋 I'm **Baymax**, your personal healthcare companion.

I'm here to help you with:
- 🩺 **Symptom Assessment** — Describe what you're feeling
- 📋 **Health Guidance** — Get safe self-care recommendations
- 📅 **Appointment Scheduling** — Book visits with healthcare providers
- 💬 **General Questions** — Ask me anything health-related

How can I help you today?`,
  timestamp: formatTime(),
}

export default function ChatScreen() {
  const { patientId } = usePatient()
  const [messages, setMessages] = useState([WELCOME_MESSAGE])
  const [isTyping, setIsTyping] = useState(false)
  const messagesEndRef = useRef(null)
  const chatContainerRef = useRef(null)

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, isTyping, scrollToBottom])

  const handleSend = useCallback(async (text) => {
    const userMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: formatTime(),
    }

    setMessages((prev) => [...prev, userMessage])
    setIsTyping(true)

    try {
      const data = await sendMessage(text, patientId)
      const botMessage = {
        id: `bot-${Date.now()}`,
        role: 'assistant',
        content: data.response,
        timestamp: formatTime(),
        riskFlag: data.risk_flag,
        intent: data.intent,
      }
      setMessages((prev) => [...prev, botMessage])
    } catch (err) {
      const errorMessage = {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: '⚠️ I encountered an issue processing your request. Please try again.',
        timestamp: formatTime(),
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsTyping(false)
    }
  }, [patientId])

  return (
    <div className="flex flex-col h-screen bg-gradient-to-br from-baymax-50/50 via-white to-surface-100">
      <ChatHeader />

      {/* Messages Area */}
      <main
        ref={chatContainerRef}
        className="flex-1 overflow-y-auto px-4 sm:px-6 py-6"
      >
        <div className="max-w-4xl mx-auto space-y-5">
          {/* Session badge */}
          <div className="flex justify-center animate-fade-in">
            <div className="inline-flex items-center gap-2 bg-baymax-50/80 border border-baymax-200/40 text-baymax-700 text-xs font-medium px-4 py-1.5 rounded-full">
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z" />
              </svg>
              Secure session for {patientId}
            </div>
          </div>

          {messages.map((msg) => (
            <ChatBubble key={msg.id} message={msg} />
          ))}

          {isTyping && <TypingIndicator />}

          <div ref={messagesEndRef} />
        </div>

        {/* Empty state watermark (visible when few messages) */}
        {messages.length <= 1 && (
          <div className="flex flex-col items-center justify-center mt-16 opacity-[0.07] pointer-events-none select-none">
            <BaymaxLogo size={120} />
          </div>
        )}
      </main>

      <ChatInput onSend={handleSend} disabled={isTyping} />
    </div>
  )
}

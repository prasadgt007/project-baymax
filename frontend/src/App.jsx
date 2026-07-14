import { useState, useRef, useEffect, useCallback } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { MeshDistortMaterial } from '@react-three/drei'
import { motion, AnimatePresence } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import * as THREE from 'three'
import { Send, LogOut, Upload, FileText, Clock, User, Stethoscope, X, CheckCircle, AlertCircle, Loader2 } from 'lucide-react'
import { sendMessage, ingestDocument, fetchBrief, initializeSession } from './services/api'

// ─── Glass panel style ────────────────────────────────────────────────────────
const GLASS = {
  background: 'rgba(255,255,255,0.04)',
  backdropFilter: 'blur(32px) saturate(160%)',
  WebkitBackdropFilter: 'blur(32px) saturate(160%)',
  border: '1px solid rgba(255,255,255,0.09)',
  borderRadius: '20px',
}

const GLASS_DARK = {
  background: 'rgba(0,0,0,0.25)',
  backdropFilter: 'blur(24px) saturate(140%)',
  WebkitBackdropFilter: 'blur(24px) saturate(140%)',
  border: '1px solid rgba(255,255,255,0.07)',
  borderRadius: '16px',
}

const ROSE_BTN = {
  background: 'linear-gradient(135deg, #9f1239, #be185d)',
  boxShadow: '0 4px 20px rgba(159,18,57,0.45)',
}

// ─── Default welcome message (used as fallback) ──────────────────────────────
const DEFAULT_WELCOME = "Hello! I'm **Baymax**, your personal healthcare companion. 🏥\n\nI'm here to help you with symptom analysis and medical appointment scheduling.\n\nHow are you feeling today?"

// ─── Document type options ────────────────────────────────────────────────────
const DOC_TYPES = [
  { value: 'report', label: 'Medical Report' },
  { value: 'xray', label: 'X-Ray Report' },
  { value: 'blood_test', label: 'Blood Test' },
  { value: 'prescription', label: 'Prescription' },
]

// ─── Three.js: Blob ───────────────────────────────────────────────────────────
function HeroBlob({ mouse }) {
  const meshRef = useRef()
  const lightRef1 = useRef()
  const lightRef2 = useRef()

  useFrame((state) => {
    const t = state.clock.elapsedTime
    const mx = mouse.current[0]
    const my = mouse.current[1]

    if (meshRef.current) {
      meshRef.current.rotation.x = t * 0.06 + my * 0.15
      meshRef.current.rotation.y = t * 0.09 + mx * 0.15
      meshRef.current.rotation.z = t * 0.04
      const breathe = 1 + Math.sin(t * 0.5) * 0.025
      meshRef.current.scale.setScalar(breathe)
    }
    if (lightRef1.current) {
      lightRef1.current.position.x = Math.sin(t * 0.4) * 5
      lightRef1.current.position.y = Math.cos(t * 0.3) * 3
      lightRef1.current.position.z = Math.cos(t * 0.5) * 4 + 3
    }
    if (lightRef2.current) {
      lightRef2.current.position.x = Math.cos(t * 0.35) * 6
      lightRef2.current.position.y = Math.sin(t * 0.28) * 4
      lightRef2.current.position.z = Math.sin(t * 0.45) * 3 + 2
    }
  })

  return (
    <>
      <ambientLight intensity={0.15} />
      <pointLight ref={lightRef1} color="#be185d" intensity={3.5} distance={12} />
      <pointLight ref={lightRef2} color="#9f1239" intensity={2.8} distance={14} />
      <pointLight position={[0, 0, 6]} color="#fda4af" intensity={1.2} distance={10} />

      {/* Outer haze */}
      <mesh>
        <sphereGeometry args={[2.55, 64, 64]} />
        <MeshDistortMaterial color="#7a0828" transparent opacity={0.08} distort={0.55} speed={1.8} roughness={0} />
      </mesh>

      {/* Main body */}
      <mesh ref={meshRef}>
        <sphereGeometry args={[2.2, 128, 128]} />
        <MeshDistortMaterial color="#9f1239" transparent opacity={0.92} distort={0.45} speed={2.2} roughness={0.05} metalness={0.1} envMapIntensity={1} />
      </mesh>

      {/* Inner glowing core */}
      <mesh>
        <sphereGeometry args={[1.3, 64, 64]} />
        <MeshDistortMaterial color="#e11d48" transparent opacity={0.35} distort={0.3} speed={3} roughness={0} emissive="#be185d" emissiveIntensity={0.6} />
      </mesh>
    </>
  )
}

function Scene({ mouse }) {
  return (
    <Canvas
      className="absolute inset-0"
      camera={{ position: [0, 0, 7], fov: 50 }}
      gl={{ antialias: true, toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 1.2 }}
      style={{ position: 'absolute', inset: 0 }}
    >
      <HeroBlob mouse={mouse} />
    </Canvas>
  )
}

// ─── Typing Indicator ─────────────────────────────────────────────────────────
function TypingIndicator() {
  return (
    <div className="flex justify-start mb-3">
      <div className="w-6 h-6 flex items-center justify-center shrink-0 mr-2 mt-0.5">
        <img src="/baymax-logo.png" alt="Baymax" className="w-full h-full object-contain drop-shadow-md" />
      </div>
      <div className="px-4 py-3 rounded-2xl rounded-tl-sm" style={GLASS_DARK}>
        <div className="flex gap-1.5 items-center h-4">
          {[0, 1, 2].map((i) => (
            <div key={i} className="w-1.5 h-1.5 rounded-full bg-rose-400"
              style={{ animation: `bounce 1.2s ease-in-out ${i * 0.2}s infinite` }} />
          ))}
        </div>
      </div>
    </div>
  )
}

// ─── Chat Bubble ──────────────────────────────────────────────────────────────
function ChatBubble({ msg }) {
  const isUser = msg.role === 'user'
  return (
    <motion.div
      initial={{ opacity: 0, y: 12, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: 'spring', stiffness: 280, damping: 28 }}
      className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3`}
    >
      {!isUser && (
        <div className="w-6 h-6 flex items-center justify-center shrink-0 mr-2 mt-0.5">
          <img src="/baymax-logo.png" alt="Baymax" className="w-full h-full object-contain drop-shadow-md" />
        </div>
      )}
      <div
        className={`px-4 py-3 text-sm leading-relaxed max-w-[80%] ${isUser ? 'rounded-2xl rounded-tr-sm' : 'rounded-2xl rounded-tl-sm'}`}
        style={isUser
          ? { background: 'linear-gradient(135deg, #9f1239, #be185d)', color: 'white', boxShadow: '0 4px 16px rgba(159,18,57,0.35)' }
          : { ...GLASS_DARK, color: 'rgba(255,255,255,0.88)' }
        }
      >
        <ReactMarkdown
          components={{
            p: ({ children }) => <p className="mb-1 last:mb-0">{children}</p>,
            strong: ({ children }) => <strong className="font-semibold text-rose-300">{children}</strong>,
            ul: ({ children }) => <ul className="list-disc list-inside space-y-0.5 mt-1">{children}</ul>,
            li: ({ children }) => <li className="text-white/80">{children}</li>,
            hr: () => <hr className="my-2 border-white/10" />,
            em: ({ children }) => <em className="text-white/60">{children}</em>,
            blockquote: ({ children }) => (
              <blockquote className="border-l-2 border-rose-500/50 pl-3 my-1 text-white/60">{children}</blockquote>
            ),
            table: ({ children }) => <table className="text-xs w-full mt-1">{children}</table>,
            th: ({ children }) => <th className="text-left text-rose-300 pr-4">{children}</th>,
            td: ({ children }) => <td className="pr-4 text-white/70">{children}</td>,
          }}
        >
          {msg.content}
        </ReactMarkdown>
      </div>
    </motion.div>
  )
}

// ─── Slot Chip ────────────────────────────────────────────────────────────────
function SlotChip({ slot, onSelect }) {
  return (
    <motion.button
      whileHover={{ scale: 1.05, boxShadow: '0 4px 20px rgba(159,18,57,0.5)' }}
      whileTap={{ scale: 0.95 }}
      onClick={() => onSelect(slot)}
      className="flex items-center gap-2 px-4 py-2 text-xs font-medium text-white rounded-full cursor-pointer transition-colors"
      style={{
        background: 'rgba(159,18,57,0.2)',
        border: '1px solid rgba(190,24,93,0.5)',
      }}
    >
      <Clock size={11} className="text-rose-400" />
      {slot.label}
    </motion.button>
  )
}

// ─── Main App ─────────────────────────────────────────────────────────────────
export default function App() {
  const mouse = useRef([0, 0])

  // Phase: 'login' | 'initializing' | 'chat' | 'dashboard'
  const [phase, setPhase] = useState('login')
  const [userRole, setUserRole] = useState('patient')
  const [patientId, setPatientId] = useState('')
  const [inputId, setInputId] = useState('')
  const [loginError, setLoginError] = useState('')
  const [sessionData, setSessionData] = useState(null)

  // Chat state
  const [messages, setMessages] = useState([])
  const [inputText, setInputText] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [availableSlots, setAvailableSlots] = useState([])
  const messagesEndRef = useRef(null)

  // Employee dashboard state
  const [uploadPatientId, setUploadPatientId] = useState('')
  const [uploadFile, setUploadFile] = useState(null)
  const [uploadDocType, setUploadDocType] = useState('report')
  const [uploadStatus, setUploadStatus] = useState(null) // null|'uploading'|'success'|'error'
  const [uploadMsg, setUploadMsg] = useState('')
  const [briefPatientId, setBriefPatientId] = useState('')
  const [briefContent, setBriefContent] = useState(null)
  const [briefLoading, setBriefLoading] = useState(false)
  const [briefError, setBriefError] = useState('')
  const [dragOver, setDragOver] = useState(false)
  const fileInputRef = useRef(null)

  // Mouse parallax
  useEffect(() => {
    const handleMouseMove = (e) => {
      mouse.current = [
        (e.clientX / window.innerWidth - 0.5) * 2,
        -(e.clientY / window.innerHeight - 0.5) * 2,
      ]
    }
    window.addEventListener('mousemove', handleMouseMove)
    return () => window.removeEventListener('mousemove', handleMouseMove)
  }, [])

  // Auto-scroll chat
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping, availableSlots])

  // ── Login with Session Initialization ─────────────────────────────────────
  const handleLogin = async (e) => {
    e.preventDefault()
    const id = inputId.trim().toUpperCase()
    if (!id) { setLoginError('Please enter an ID to continue.'); return }
    setLoginError('')
    setPatientId(id)

    if (userRole === 'hospital_employee') {
      // Employees go directly to dashboard (no session init needed)
      setMessages([])
      setAvailableSlots([])
      setPhase('dashboard')
      return
    }

    // Patient flow: initialize session with proactive context loading
    setPhase('initializing')

    try {
      const data = await initializeSession(id, userRole)
      setSessionData(data)

      // Use the personalised greeting from the server
      const greeting = data.greeting || DEFAULT_WELCOME
      setMessages([{
        id: 'welcome',
        role: 'assistant',
        content: greeting,
      }])
      setAvailableSlots([])
      setPhase('chat')
    } catch (err) {
      console.error('[Session Init] Error:', err)
      // Fallback: proceed with default greeting
      setMessages([{
        id: 'welcome',
        role: 'assistant',
        content: DEFAULT_WELCOME,
      }])
      setAvailableSlots([])
      setPhase('chat')
    }
  }

  const handleLogout = () => {
    setPhase('login')
    setInputId('')
    setPatientId('')
    setMessages([])
    setAvailableSlots([])
    setSessionData(null)
    setBriefContent(null)
    setUploadFile(null)
    setUploadStatus(null)
    setUploadDocType('report')
  }

  // ── Chat (Patient) ────────────────────────────────────────────────────────
  const handleSend = useCallback(async (text) => {
    const msg = text || inputText
    if (!msg.trim() || isTyping) return

    setInputText('')
    setMessages((prev) => [...prev, { id: `u-${Date.now()}`, role: 'user', content: msg }])
    setIsTyping(true)
    setAvailableSlots([])

    try {
      const data = await sendMessage(msg, patientId, userRole)
      setIsTyping(false)
      setMessages((prev) => [
        ...prev,
        { id: `b-${Date.now()}`, role: 'assistant', content: data.response },
      ])
      if (data.available_slots?.length > 0) {
        setAvailableSlots(data.available_slots)
      }
    } catch (err) {
      setIsTyping(false)
      setMessages((prev) => [
        ...prev,
        { id: `err-${Date.now()}`, role: 'assistant', content: `⚠️ ${err.message}` },
      ])
    }
  }, [inputText, isTyping, patientId, userRole])

  const handleSlotSelect = useCallback(async (slot) => {
    setAvailableSlots([])
    handleSend(`Book the ${slot.label} slot <!-- slot_id: ${slot.slot_id} -->`)
  }, [handleSend])

  const handleChatKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // ── Document Upload (Employee) ─────────────────────────────────────────────
  const handleFileDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer?.files?.[0]
    if (file) {
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        setUploadStatus('error')
        setUploadMsg('Only PDF files are supported.')
        return
      }
      setUploadFile(file)
      setUploadStatus(null)
    }
  }

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0]
    if (file) {
      setUploadFile(file)
      setUploadStatus(null)
    }
  }

  const handleUpload = async () => {
    if (!uploadFile || !uploadPatientId.trim()) {
      setUploadStatus('error')
      setUploadMsg('Please provide a Patient ID and select a PDF file.')
      return
    }
    setUploadStatus('uploading')
    setUploadMsg('')
    try {
      const res = await ingestDocument(
        uploadPatientId.trim().toUpperCase(),
        'hospital_employee',
        uploadFile,
        uploadDocType,
      )
      setUploadStatus('success')
      setUploadMsg(res.message || `Ingested ${res.chars_ingested?.toLocaleString() || '?'} characters.`)
      setUploadFile(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
    } catch (err) {
      setUploadStatus('error')
      setUploadMsg(err.message || 'Upload failed.')
    }
  }

  // ── Brief Fetch (Employee) ─────────────────────────────────────────────────
  const handleFetchBrief = async () => {
    if (!briefPatientId.trim()) return
    setBriefLoading(true)
    setBriefError('')
    setBriefContent(null)
    try {
      const res = await fetchBrief(briefPatientId.trim().toUpperCase())
      setBriefContent(res.brief)
    } catch (err) {
      setBriefError(err.message || 'Failed to fetch brief.')
    } finally {
      setBriefLoading(false)
    }
  }

  // ── Render ────────────────────────────────────────────────────────────────────
  return (
    <div
      className="relative w-screen h-screen overflow-hidden"
      style={{ background: '#09060d', fontFamily: "'Inter', sans-serif" }}
    >
      <Scene mouse={mouse} />

      {/* Atmospheric radial glow */}
      <div className="absolute inset-0 pointer-events-none" style={{
        background: 'radial-gradient(ellipse 70% 60% at 50% 50%, rgba(159,18,57,0.13) 0%, transparent 70%)',
      }} />

      {/* ── LOGIN ── */}
      <AnimatePresence>
        {phase === 'login' && (
          <motion.div
            key="login"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 flex items-center justify-center px-4"
          >
            <motion.div
              initial={{ opacity: 0, y: 24, scale: 0.96 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -16, scale: 0.97 }}
              transition={{ type: 'spring', stiffness: 260, damping: 28 }}
              style={{ ...GLASS, padding: '2.5rem 2rem', width: '100%', maxWidth: '380px' }}
            >
              {/* Logo */}
              <div className="flex flex-col items-center mb-7">
                <div className="w-16 h-16 flex items-center justify-center mb-3">
                  <img src="/baymax-logo.png" alt="Baymax" className="w-full h-full object-contain drop-shadow-[0_8px_24px_rgba(159,18,57,0.5)]" />
                </div>
                <h1 className="text-xl font-bold text-white tracking-tight">Baymax</h1>
                <p className="text-white/40 text-xs mt-1 tracking-wide">AI Healthcare Companion</p>
              </div>

              {/* Role Toggle */}
              <div className="mb-5 flex rounded-xl overflow-hidden" style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)' }}>
                <button
                  type="button"
                  onClick={() => setUserRole('patient')}
                  className="flex-1 py-2.5 flex items-center justify-center gap-2 text-xs font-medium transition-all duration-200"
                  style={userRole === 'patient'
                    ? { ...ROSE_BTN, color: 'white' }
                    : { color: 'rgba(255,255,255,0.4)', background: 'transparent' }
                  }
                >
                  <User size={13} /> Patient
                </button>
                <button
                  type="button"
                  onClick={() => setUserRole('hospital_employee')}
                  className="flex-1 py-2.5 flex items-center justify-center gap-2 text-xs font-medium transition-all duration-200"
                  style={userRole === 'hospital_employee'
                    ? { ...ROSE_BTN, color: 'white' }
                    : { color: 'rgba(255,255,255,0.4)', background: 'transparent' }
                  }
                >
                  <Stethoscope size={13} /> Hospital Staff
                </button>
              </div>

              {/* ID Input */}
              <form onSubmit={handleLogin}>
                <label className="block text-white/50 text-[10px] uppercase tracking-widest mb-1.5">
                  {userRole === 'patient' ? 'Patient ID' : 'Staff ID'}
                </label>
                <input
                  id="login-id-input"
                  type="text"
                  value={inputId}
                  onChange={(e) => { setInputId(e.target.value); setLoginError('') }}
                  placeholder={userRole === 'patient' ? 'e.g. P001' : 'e.g. E001'}
                  className="w-full px-4 py-3 rounded-xl text-sm text-white placeholder-white/20 outline-none focus:ring-1 focus:ring-rose-600/60 transition-all mb-3"
                  style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)' }}
                  autoComplete="off"
                />
                {loginError && (
                  <p className="text-rose-400 text-xs mb-3">{loginError}</p>
                )}
                <motion.button
                  type="submit"
                  whileHover={{ scale: 1.02, boxShadow: '0 6px 28px rgba(159,18,57,0.55)' }}
                  whileTap={{ scale: 0.98 }}
                  className="w-full py-3 rounded-xl text-sm font-semibold text-white transition-all"
                  style={ROSE_BTN}
                >
                  {userRole === 'patient' ? 'Start Consultation' : 'Open Dashboard'}
                </motion.button>
              </form>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── INITIALIZING SESSION ── */}
      <AnimatePresence>
        {phase === 'initializing' && (
          <motion.div
            key="initializing"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 flex items-center justify-center px-4"
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ type: 'spring', stiffness: 260, damping: 28 }}
              className="flex flex-col items-center gap-5"
              style={{ ...GLASS, padding: '3rem 2.5rem', maxWidth: '340px' }}
            >
              <div className="w-14 h-14 flex items-center justify-center">
                <img src="/baymax-logo.png" alt="Baymax" className="w-full h-full object-contain drop-shadow-[0_8px_24px_rgba(159,18,57,0.5)]" />
              </div>
              <div className="flex flex-col items-center gap-3">
                <Loader2 size={24} className="text-rose-400 animate-spin" />
                <p className="text-white/60 text-sm font-medium">Initializing your session…</p>
                <p className="text-white/30 text-xs text-center">Loading your medical profile and records</p>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── PATIENT CHAT ── */}
      <AnimatePresence>
        {phase === 'chat' && (
          <motion.div
            key="chat"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 flex items-center justify-center px-4 py-6"
          >
            <motion.div
              initial={{ opacity: 0, y: 20, scale: 0.96 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{ type: 'spring', stiffness: 260, damping: 28 }}
              className="flex flex-col w-full max-w-lg"
              style={{ ...GLASS, height: 'min(88vh, 680px)' }}
            >
              {/* Header */}
              <div className="flex items-center justify-between px-4 py-3 shrink-0" style={{ borderBottom: '1px solid rgba(255,255,255,0.07)' }}>
                <div className="flex items-center gap-2.5">
                  <div className="w-9 h-9 flex items-center justify-center">
                    <img src="/baymax-logo.png" alt="Baymax" className="w-full h-full object-contain drop-shadow-[0_4px_12px_rgba(159,18,57,0.4)]" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-white leading-none">Baymax</p>
                    <p className="text-[10px] text-white/35 mt-0.5">Healthcare AI · {patientId}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full" style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)' }}>
                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" style={{ boxShadow: '0 0 6px #34d399' }} />
                    <span className="text-[9px] text-white/40 font-medium">LIVE</span>
                  </div>
                  <button
                    onClick={handleLogout}
                    className="w-8 h-8 flex items-center justify-center rounded-lg text-white/30 hover:text-white/70 transition-colors"
                    style={{ background: 'rgba(255,255,255,0.04)' }}
                  >
                    <LogOut size={14} />
                  </button>
                </div>
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto px-4 py-4 space-y-1" style={{ scrollbarWidth: 'none' }}>
                {messages.map((msg) => (
                  <ChatBubble key={msg.id} msg={msg} />
                ))}
                {isTyping && <TypingIndicator />}
                <div ref={messagesEndRef} />
              </div>

              {/* Slot Chips */}
              <AnimatePresence>
                {availableSlots.length > 0 && (
                  <motion.div
                    key="slots"
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="px-4 py-3 shrink-0"
                    style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}
                  >
                    <p className="text-white/35 text-[9px] uppercase tracking-widest mb-2.5">Select a time slot</p>
                    <div className="flex flex-wrap gap-2">
                      {availableSlots.map((slot) => (
                        <SlotChip key={slot.slot_id} slot={slot} onSelect={handleSlotSelect} />
                      ))}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Input */}
              <div className="px-4 py-3 shrink-0" style={{ borderTop: '1px solid rgba(255,255,255,0.07)' }}>
                <div className="flex items-end gap-2">
                  <textarea
                    id="chat-input"
                    rows={1}
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    onKeyDown={handleChatKeyDown}
                    placeholder="Describe your symptoms…"
                    className="flex-1 resize-none text-sm text-white placeholder-white/20 outline-none leading-relaxed py-2.5 px-3 rounded-xl transition-all"
                    style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', minHeight: '42px', maxHeight: '120px', scrollbarWidth: 'none' }}
                    onInput={(e) => { e.target.style.height = 'auto'; e.target.style.height = e.target.scrollHeight + 'px' }}
                    disabled={isTyping}
                  />
                  <motion.button
                    whileHover={{ scale: 1.08 }}
                    whileTap={{ scale: 0.93 }}
                    onClick={() => handleSend()}
                    disabled={!inputText.trim() || isTyping}
                    className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 transition-all disabled:opacity-30"
                    style={ROSE_BTN}
                  >
                    <Send size={15} className="text-white" style={{ transform: 'translateX(1px)' }} />
                  </motion.button>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── EMPLOYEE DASHBOARD ── */}
      <AnimatePresence>
        {phase === 'dashboard' && (
          <motion.div
            key="dashboard"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 flex flex-col px-4 py-5 gap-3"
          >
            {/* Dashboard Header */}
            <motion.div
              initial={{ opacity: 0, y: -12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="flex items-center justify-between shrink-0 px-4 py-3 rounded-2xl"
              style={GLASS}
            >
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 flex items-center justify-center">
                  <img src="/baymax-logo.png" alt="Baymax" className="w-full h-full object-contain" />
                </div>
                <div>
                  <p className="text-white font-semibold text-sm leading-none">Baymax — Hospital Dashboard</p>
                  <p className="text-white/35 text-[10px] mt-0.5">Staff ID: {patientId} · Hospital Employee Mode</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full" style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)' }}>
                  <div className="w-1.5 h-1.5 rounded-full bg-amber-400" style={{ boxShadow: '0 0 6px #fbbf24' }} />
                  <span className="text-[9px] text-white/40 font-medium">STAFF</span>
                </div>
                <button
                  onClick={handleLogout}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-white/40 hover:text-white/70 text-xs transition-colors"
                  style={{ background: 'rgba(255,255,255,0.04)' }}
                >
                  <LogOut size={12} /> Logout
                </button>
              </div>
            </motion.div>

            {/* Dashboard Panes */}
            <div className="flex gap-4 flex-1 min-h-0">

              {/* ── LEFT PANE: Document Upload ── */}
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.15, type: 'spring', stiffness: 240, damping: 28 }}
                className="flex flex-col w-80 shrink-0"
                style={{ ...GLASS, padding: '1.5rem' }}
              >
                <div className="flex items-center gap-2 mb-5 shrink-0">
                  <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={ROSE_BTN}>
                    <Upload size={14} className="text-white" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-white leading-none">Document Manager</p>
                    <p className="text-[10px] text-white/35 mt-0.5">Ingest PDF records into vector DB</p>
                  </div>
                </div>

                {/* Patient ID for upload */}
                <label className="text-white/40 text-[10px] uppercase tracking-widest mb-1.5 shrink-0">Patient ID</label>
                <input
                  id="upload-patient-id"
                  type="text"
                  value={uploadPatientId}
                  onChange={(e) => setUploadPatientId(e.target.value)}
                  placeholder="e.g. P001"
                  className="w-full px-3 py-2.5 rounded-xl text-sm text-white placeholder-white/20 outline-none mb-3 shrink-0"
                  style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)' }}
                />

                {/* Document Type Selector */}
                <label className="text-white/40 text-[10px] uppercase tracking-widest mb-1.5 shrink-0">Document Type</label>
                <select
                  id="upload-doc-type"
                  value={uploadDocType}
                  onChange={(e) => setUploadDocType(e.target.value)}
                  className="w-full px-3 py-2.5 rounded-xl text-sm text-white outline-none mb-4 shrink-0 appearance-none cursor-pointer"
                  style={{
                    background: 'rgba(255,255,255,0.06)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='rgba(255,255,255,0.3)' stroke-width='2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E")`,
                    backgroundRepeat: 'no-repeat',
                    backgroundPosition: 'right 12px center',
                  }}
                >
                  {DOC_TYPES.map((dt) => (
                    <option key={dt.value} value={dt.value} style={{ background: '#1a1a2e', color: 'white' }}>
                      {dt.label}
                    </option>
                  ))}
                </select>

                {/* Drop Zone */}
                <div
                  onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={handleFileDrop}
                  onClick={() => fileInputRef.current?.click()}
                  className="flex-1 min-h-0 flex flex-col items-center justify-center text-center cursor-pointer rounded-2xl transition-all mb-4"
                  style={{
                    border: `2px dashed ${dragOver ? 'rgba(190,24,93,0.7)' : 'rgba(255,255,255,0.12)'}`,
                    background: dragOver ? 'rgba(159,18,57,0.08)' : 'rgba(255,255,255,0.02)',
                    padding: '1.5rem 1rem',
                    minHeight: '120px',
                  }}
                >
                  {uploadFile ? (
                    <>
                      <FileText size={28} className="text-rose-400 mb-2" />
                      <p className="text-white text-xs font-medium">{uploadFile.name}</p>
                      <p className="text-white/35 text-[10px] mt-1">{(uploadFile.size / 1024).toFixed(1)} KB</p>
                      <button
                        onClick={(e) => { e.stopPropagation(); setUploadFile(null); setUploadStatus(null) }}
                        className="mt-2 text-white/30 hover:text-white/60 transition-colors"
                      >
                        <X size={14} />
                      </button>
                    </>
                  ) : (
                    <>
                      <Upload size={24} className="text-white/20 mb-2" />
                      <p className="text-white/40 text-xs">Drop PDF here or click to browse</p>
                      <p className="text-white/20 text-[10px] mt-1">PDF files only</p>
                    </>
                  )}
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf"
                    className="hidden"
                    onChange={handleFileSelect}
                  />
                </div>

                {/* Upload status */}
                <AnimatePresence>
                  {uploadStatus && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }}
                      className="mb-3 shrink-0"
                    >
                      <div className="flex items-start gap-2 px-3 py-2.5 rounded-xl"
                        style={{
                          background: uploadStatus === 'success' ? 'rgba(52,211,153,0.08)' : uploadStatus === 'error' ? 'rgba(244,63,94,0.08)' : 'rgba(255,255,255,0.04)',
                          border: `1px solid ${uploadStatus === 'success' ? 'rgba(52,211,153,0.2)' : uploadStatus === 'error' ? 'rgba(244,63,94,0.2)' : 'rgba(255,255,255,0.08)'}`,
                        }}
                      >
                        {uploadStatus === 'uploading' && <Loader2 size={13} className="text-white/40 mt-0.5 animate-spin shrink-0" />}
                        {uploadStatus === 'success' && <CheckCircle size={13} className="text-emerald-400 mt-0.5 shrink-0" />}
                        {uploadStatus === 'error' && <AlertCircle size={13} className="text-rose-400 mt-0.5 shrink-0" />}
                        <p className="text-[11px] leading-relaxed"
                          style={{ color: uploadStatus === 'success' ? '#34d399' : uploadStatus === 'error' ? '#fb7185' : 'rgba(255,255,255,0.5)' }}
                        >
                          {uploadStatus === 'uploading' ? 'Embedding document into vector store…' : uploadMsg}
                        </p>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* Upload button */}
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={handleUpload}
                  disabled={uploadStatus === 'uploading'}
                  className="w-full py-2.5 rounded-xl text-sm font-semibold text-white transition-all shrink-0 disabled:opacity-40"
                  style={ROSE_BTN}
                >
                  {uploadStatus === 'uploading' ? 'Ingesting…' : 'Upload & Ingest'}
                </motion.button>
              </motion.div>

              {/* ── RIGHT PANE: Pre-Consultation Briefs ── */}
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.2, type: 'spring', stiffness: 240, damping: 28 }}
                className="flex-1 flex flex-col min-w-0"
                style={{ ...GLASS, padding: '1.5rem' }}
              >
                <div className="flex items-center gap-2 mb-5 shrink-0">
                  <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={ROSE_BTN}>
                    <FileText size={14} className="text-white" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-white leading-none">Pre-Consultation Briefs</p>
                    <p className="text-[10px] text-white/35 mt-0.5">AI-generated clinical summaries</p>
                  </div>
                </div>

                {/* Brief fetch form */}
                <div className="flex gap-2 mb-4 shrink-0">
                  <input
                    id="brief-patient-id"
                    type="text"
                    value={briefPatientId}
                    onChange={(e) => { setBriefPatientId(e.target.value); setBriefError('') }}
                    onKeyDown={(e) => e.key === 'Enter' && handleFetchBrief()}
                    placeholder="Enter Patient ID (e.g. P001)"
                    className="flex-1 px-3 py-2 rounded-xl text-sm text-white placeholder-white/20 outline-none"
                    style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)' }}
                  />
                  <motion.button
                    whileHover={{ scale: 1.04 }}
                    whileTap={{ scale: 0.96 }}
                    onClick={handleFetchBrief}
                    disabled={briefLoading || !briefPatientId.trim()}
                    className="px-4 py-2 rounded-xl text-xs font-semibold text-white transition-all disabled:opacity-40 flex items-center gap-1.5"
                    style={ROSE_BTN}
                  >
                    {briefLoading ? <Loader2 size={13} className="animate-spin" /> : <FileText size={13} />}
                    {briefLoading ? 'Loading…' : 'Fetch Brief'}
                  </motion.button>
                </div>

                {/* Brief content */}
                <div className="flex-1 overflow-y-auto rounded-2xl" style={{ scrollbarWidth: 'thin', scrollbarColor: 'rgba(159,18,57,0.3) transparent' }}>
                  {briefError && (
                    <div className="flex items-center gap-2 px-3 py-2.5 rounded-xl mb-3" style={{ background: 'rgba(244,63,94,0.08)', border: '1px solid rgba(244,63,94,0.2)' }}>
                      <AlertCircle size={14} className="text-rose-400 shrink-0" />
                      <p className="text-rose-400 text-xs">{briefError}</p>
                    </div>
                  )}

                  {briefContent ? (
                    <motion.div
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="px-5 py-4 rounded-2xl"
                      style={{ background: 'rgba(0,0,0,0.2)', border: '1px solid rgba(255,255,255,0.07)' }}
                    >
                      <div className="prose prose-invert prose-sm max-w-none text-white/80">
                        <ReactMarkdown
                          components={{
                            h2: ({ children }) => <h2 className="text-base font-bold text-white mb-3 mt-0">{children}</h2>,
                            h3: ({ children }) => <h3 className="text-sm font-semibold text-rose-300 mb-2 mt-4">{children}</h3>,
                            p: ({ children }) => <p className="text-sm text-white/75 mb-2">{children}</p>,
                            ul: ({ children }) => <ul className="space-y-1 mb-2">{children}</ul>,
                            li: ({ children }) => <li className="text-sm text-white/70 ml-3">• {children}</li>,
                            strong: ({ children }) => <strong className="text-white font-semibold">{children}</strong>,
                            em: ({ children }) => <em className="text-white/50">{children}</em>,
                            hr: () => <hr className="border-white/10 my-3" />,
                            blockquote: ({ children }) => (
                              <blockquote className="border-l-2 border-rose-500/50 pl-3 py-1 my-2 rounded-r-lg text-sm" style={{ background: 'rgba(159,18,57,0.08)' }}>
                                {children}
                              </blockquote>
                            ),
                            table: ({ children }) => <table className="w-full text-xs border-collapse mb-3">{children}</table>,
                            th: ({ children }) => <th className="text-left text-rose-300 font-semibold pb-1 pr-4">{children}</th>,
                            td: ({ children }) => <td className="text-white/65 py-0.5 pr-4">{children}</td>,
                            code: ({ children }) => <code className="px-1.5 py-0.5 rounded text-rose-300 text-xs" style={{ background: 'rgba(159,18,57,0.15)' }}>{children}</code>,
                          }}
                        >
                          {briefContent}
                        </ReactMarkdown>
                      </div>
                    </motion.div>
                  ) : !briefLoading && !briefError ? (
                    <div className="h-full flex flex-col items-center justify-center text-center py-12">
                      <FileText size={36} className="text-white/10 mb-3" />
                      <p className="text-white/25 text-sm">Enter a Patient ID above to load their brief</p>
                      <p className="text-white/15 text-xs mt-1.5">Briefs are generated after appointment confirmation</p>
                    </div>
                  ) : null}

                  {briefLoading && (
                    <div className="h-full flex items-center justify-center py-12">
                      <div className="flex flex-col items-center gap-3">
                        <Loader2 size={28} className="text-rose-400/60 animate-spin" />
                        <p className="text-white/30 text-xs">Generating clinical brief…</p>
                      </div>
                    </div>
                  )}
                </div>
              </motion.div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <style>{`
        @keyframes bounce {
          0%, 60%, 100% { transform: translateY(0); }
          30% { transform: translateY(-5px); }
        }
        * { box-sizing: border-box; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(159,18,57,0.3); border-radius: 4px; }
      `}</style>
    </div>
  )
}

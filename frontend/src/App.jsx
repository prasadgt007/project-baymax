import { useState, useRef, useEffect, useCallback } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { MeshDistortMaterial, Float } from '@react-three/drei'
import { motion, AnimatePresence } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import * as THREE from 'three'
import { Send, LogOut, HeartPulse } from 'lucide-react'
import { sendMessage } from './services/api'

// ─── Mock fallback (real API wired above) ────────────────────────────────────
async function mockSendMessage(userMessage, patientId) {
  await new Promise((r) => setTimeout(r, 1800))
  return {
    response: `**Baymax** responding for patient **${patientId}**.\n\nI received: *"${userMessage}"*\n\n- Analyzing symptoms...\n- Cross-referencing medical history\n- Generating care recommendations\n\n> This is a **mock response**. Connect to the FastAPI backend for live responses.`,
  }
}

// ─── The Guardnet-style hero blob ────────────────────────────────────────────
// A large, slowly morphing 3D sphere that reacts to mouse movement.
// Colors: deep rose/muted crimson — sophisticated, not electric.
function HeroBlob({ mouse }) {
  const meshRef = useRef()
  const lightRef1 = useRef()
  const lightRef2 = useRef()

  useFrame((state) => {
    const t = state.clock.elapsedTime
    const mx = mouse.current[0]
    const my = mouse.current[1]

    if (meshRef.current) {
      // Very slow autonomous rotation
      meshRef.current.rotation.x = t * 0.06 + my * 0.15
      meshRef.current.rotation.y = t * 0.09 + mx * 0.15
      meshRef.current.rotation.z = t * 0.04

      // Subtle scale breathe
      const breathe = 1 + Math.sin(t * 0.5) * 0.025
      meshRef.current.scale.setScalar(breathe)
    }

    // Orbit lights slowly around the blob for dynamic depth
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
      {/* Ambient fill — very dim */}
      <ambientLight intensity={0.08} />

      {/* Primary warm rose light — orbits the blob */}
      <pointLight ref={lightRef1} intensity={6} color="#c0405a" distance={14} decay={2} />

      {/* Secondary cool highlight */}
      <pointLight ref={lightRef2} intensity={3} color="#7b2d8b" distance={12} decay={2} />

      {/* Deep back fill */}
      <pointLight position={[0, 0, -8]} intensity={1.5} color="#1a0a20" distance={20} decay={1} />

      {/* ── The main blob sphere ── */}
      <mesh ref={meshRef} position={[0, 0, 0]}>
        <sphereGeometry args={[2.8, 128, 128]} />
        <MeshDistortMaterial
          color="#7a1830"        // Deep muted crimson base
          distort={0.55}        // Strong but not chaotic
          speed={1.8}           // Slow enough to feel organic
          roughness={0.15}
          metalness={0.65}
          envMapIntensity={1.2}
        />
      </mesh>

      {/* ── Inner glow core — smaller, brighter, same center ── */}
      <mesh position={[0, 0, 0.3]}>
        <sphereGeometry args={[1.4, 64, 64]} />
        <MeshDistortMaterial
          color="#c0405a"
          distort={0.7}
          speed={2.2}
          roughness={0.05}
          metalness={0.8}
          transparent
          opacity={0.45}
        />
      </mesh>

      {/* ── Outer haze shell — very transparent, large ── */}
      <mesh position={[0, 0, 0]}>
        <sphereGeometry args={[3.6, 32, 32]} />
        <meshStandardMaterial
          color="#5a0f20"
          transparent
          opacity={0.12}
          side={THREE.BackSide}
          roughness={1}
          metalness={0}
        />
      </mesh>
    </>
  )
}

function MouseParallaxCamera({ mouse }) {
  const { camera } = useThree()
  useFrame(() => {
    // Gentle parallax — blob appears to shift with mouse
    camera.position.x += (mouse.current[0] * 0.8 - camera.position.x) * 0.025
    camera.position.y += (-mouse.current[1] * 0.5 - camera.position.y) * 0.025
    camera.lookAt(0, 0, 0)
  })
  return null
}

function Scene() {
  const mouse = useRef([0, 0])

  const handleMouseMove = useCallback((e) => {
    mouse.current = [
      (e.clientX / window.innerWidth - 0.5) * 2,
      (e.clientY / window.innerHeight - 0.5) * 2,
    ]
  }, [])

  useEffect(() => {
    window.addEventListener('mousemove', handleMouseMove)
    return () => window.removeEventListener('mousemove', handleMouseMove)
  }, [handleMouseMove])

  return (
    <Canvas
      camera={{ position: [0, 0, 7], fov: 55 }}
      style={{ position: 'absolute', inset: 0 }}
      gl={{ antialias: true, alpha: false, toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 1.2 }}
      dpr={[1, 1.5]}
    >
      <color attach="background" args={['#09060d']} />
      <fog attach="fog" args={['#09060d', 10, 28]} />
      <MouseParallaxCamera mouse={mouse} />
      <HeroBlob mouse={mouse} />
    </Canvas>
  )
}

// ─── Typing Indicator ────────────────────────────────────────────────────────
function TypingIndicator() {
  return (
    <div className="flex items-center gap-1.5 px-1 py-0.5">
      <div className="typing-dot" />
      <div className="typing-dot" />
      <div className="typing-dot" />
    </div>
  )
}

// ─── Chat Bubble ─────────────────────────────────────────────────────────────
function ChatBubble({ msg }) {
  const isUser = msg.role === 'user'
  return (
    <motion.div
      initial={{ opacity: 0, y: 14, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: 'spring', stiffness: 420, damping: 32 }}
      className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3`}
    >
      {!isUser && (
        <div className="w-6 h-6 flex items-center justify-center shrink-0 mr-2 mt-0.5">
          <img src="/baymax-logo.png" alt="Baymax" className="w-full h-full object-contain drop-shadow-md" />
        </div>
      )}
      <div
        className={`max-w-[82%] px-3.5 py-2.5 rounded-2xl text-sm leading-relaxed ${
          isUser
            ? 'bg-rose-700/90 text-white rounded-br-sm backdrop-blur-sm'
            : 'bg-white/10 text-white/90 rounded-bl-sm backdrop-blur-sm border border-white/10'
        }`}
      >
        {isUser ? (
          <span>{msg.content}</span>
        ) : (
          <div className="prose-bubble">
            <ReactMarkdown>{msg.content}</ReactMarkdown>
          </div>
        )}
      </div>
    </motion.div>
  )
}

// ─── Main App ─────────────────────────────────────────────────────────────────
const WELCOME = {
  id: 'welcome',
  role: 'assistant',
  content:
    "Hello! I'm **Baymax**, your personal healthcare companion.\n\nI can help you with:\n- **Symptom Assessment** — describe how you're feeling\n- **Health Guidance** — safe, evidence-based recommendations\n- **Appointment Scheduling** — book consultations\n\nHow can I help you today?",
}

export default function App() {
  const [phase, setPhase] = useState('login')
  const [patientId, setPatientId] = useState('')
  const [inputId, setInputId] = useState('')
  const [messages, setMessages] = useState([WELCOME])
  const [inputText, setInputText] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  const handleLogin = (e) => {
    e.preventDefault()
    if (!inputId.trim()) return
    setPatientId(inputId.trim().toUpperCase())
    setPhase('chat')
  }

  const handleLogout = () => {
    setPhase('login')
    setPatientId('')
    setInputId('')
    setMessages([WELCOME])
  }

  const handleSend = async (e) => {
    e.preventDefault()
    const text = inputText.trim()
    if (!text || isTyping) return

    setMessages((p) => [...p, { id: `u-${Date.now()}`, role: 'user', content: text }])
    setInputText('')
    setIsTyping(true)

    try {
      let data
      try {
        data = await sendMessage(text, patientId)
      } catch {
        data = await mockSendMessage(text, patientId)
      }
      setMessages((p) => [...p, { id: `b-${Date.now()}`, role: 'assistant', content: data.response }])
    } catch {
      setMessages((p) => [...p, {
        id: `e-${Date.now()}`,
        role: 'assistant',
        content: 'I encountered an issue reaching the health network. Please try again.',
      }])
    } finally {
      setIsTyping(false)
    }
  }

  return (
    <div className="relative w-full h-full overflow-hidden">

      {/* ── 3D Canvas — always visible, fills entire screen ── */}
      <Scene />

      {/* ── Radial atmospheric glow — matches the blob center ── */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: 'radial-gradient(ellipse 60% 55% at 50% 50%, rgba(160,30,60,0.18) 0%, transparent 70%)',
        }}
      />

      {/* ── Deep edge vignette ── */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: 'radial-gradient(ellipse at center, transparent 40%, rgba(9,6,13,0.75) 100%)',
        }}
      />

      {/* ══════════════════════ LOGIN ══════════════════════ */}
      <AnimatePresence>
        {phase === 'login' && (
          <motion.div
            key="login"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, scale: 0.96, y: -20 }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
            className="absolute inset-0 flex items-center justify-center px-4"
          >
            <motion.div
              initial={{ opacity: 0, y: 30, scale: 0.93 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{ delay: 0.1, duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
              className="w-full max-w-sm"
              style={{
                background: 'rgba(255,255,255,0.05)',
                backdropFilter: 'blur(28px) saturate(160%)',
                WebkitBackdropFilter: 'blur(28px) saturate(160%)',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: '24px',
                padding: '36px 32px',
                boxShadow: '0 32px 80px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.08)',
              }}
            >
              {/* Logo */}
              <div className="flex flex-col items-center mb-8">
                <div className="w-16 h-16 flex items-center justify-center mb-3">
                  <img src="/baymax-logo.png" alt="Baymax Logo" className="w-full h-full object-contain drop-shadow-[0_8px_24px_rgba(159,18,57,0.45)]" />
                </div>
                <h1 className="text-xl font-bold text-white tracking-tight">Baymax</h1>
                <p className="text-white/40 mt-1 text-xs tracking-wide">AI Healthcare Companion</p>
              </div>

              <form onSubmit={handleLogin} className="space-y-4">
                <div>
                  <label htmlFor="pid" className="block text-[11px] font-medium text-white/40 mb-1.5 uppercase tracking-widest">
                    Patient Identifier
                  </label>
                  <input
                    id="pid"
                    type="text"
                    required
                    value={inputId}
                    onChange={(e) => setInputId(e.target.value)}
                    placeholder="e.g. P001"
                    className="w-full px-4 py-2.5 text-sm text-white placeholder-white/25 focus:outline-none transition-all duration-200"
                    style={{
                      background: 'rgba(255,255,255,0.07)',
                      border: '1px solid rgba(255,255,255,0.12)',
                      borderRadius: '12px',
                    }}
                    onFocus={(e) => {
                      e.target.style.border = '1px solid rgba(190,24,93,0.7)'
                      e.target.style.boxShadow = '0 0 0 3px rgba(159,18,57,0.2)'
                    }}
                    onBlur={(e) => {
                      e.target.style.border = '1px solid rgba(255,255,255,0.12)'
                      e.target.style.boxShadow = 'none'
                    }}
                  />
                </div>
                <button
                  type="submit"
                  className="w-full text-white font-semibold py-2.5 text-sm cursor-pointer transition-all duration-200 hover:scale-[1.02] active:scale-95"
                  style={{
                    background: 'linear-gradient(135deg, #9f1239, #be185d)',
                    borderRadius: '12px',
                    boxShadow: '0 4px 20px rgba(159,18,57,0.4)',
                  }}
                  onMouseEnter={(e) => { e.target.style.boxShadow = '0 6px 28px rgba(159,18,57,0.6)' }}
                  onMouseLeave={(e) => { e.target.style.boxShadow = '0 4px 20px rgba(159,18,57,0.4)' }}
                >
                  Start Consultation
                </button>
              </form>

              <p className="text-center text-white/20 text-[10px] mt-5 tracking-wide">
                End-to-end encrypted session
              </p>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ══════════════════════ CHAT ══════════════════════ */}
      <AnimatePresence>
        {phase === 'chat' && (
          <motion.div
            key="chat"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5 }}
            className="absolute inset-0 flex items-center justify-center px-4 py-6"
          >
            <motion.div
              initial={{ opacity: 0, y: 24, scale: 0.94 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{ delay: 0.1, duration: 0.65, ease: [0.16, 1, 0.3, 1] }}
              className="flex flex-col w-full max-w-lg h-full max-h-[88vh]"
              style={{
                background: 'rgba(255,255,255,0.05)',
                backdropFilter: 'blur(32px) saturate(160%)',
                WebkitBackdropFilter: 'blur(32px) saturate(160%)',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: '24px',
                boxShadow: '0 32px 80px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.08)',
              }}
            >
              {/* ── Header ── */}
              <div
                className="shrink-0 flex items-center justify-between px-5 py-4"
                style={{ borderBottom: '1px solid rgba(255,255,255,0.08)' }}
              >
                <div className="flex items-center gap-2.5">
                  <div className="w-9 h-9 flex items-center justify-center">
                    <img src="/baymax-logo.png" alt="Baymax Logo" className="w-full h-full object-contain drop-shadow-[0_4px_12px_rgba(159,18,57,0.4)]" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-white leading-none">Baymax</p>
                    <p className="text-[10px] text-white/35 mt-0.5">Healthcare AI</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className="flex items-center gap-1.5 text-[11px] font-medium text-white/70 px-3 py-1.5"
                    style={{
                      background: 'rgba(159,18,57,0.2)',
                      border: '1px solid rgba(190,24,93,0.3)',
                      borderRadius: '99px',
                    }}
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-rose-400 animate-pulse" />
                    {patientId}
                  </span>
                  <button
                    onClick={handleLogout}
                    className="p-1.5 text-white/30 hover:text-white/80 transition-colors duration-150 cursor-pointer"
                    title="End session"
                    style={{ borderRadius: '8px' }}
                  >
                    <LogOut size={15} />
                  </button>
                </div>
              </div>

              {/* ── Messages ── */}
              <div className="flex-1 overflow-y-auto px-4 py-4 scroll-smooth">
                <AnimatePresence initial={false}>
                  {messages.map((msg) => (
                    <ChatBubble key={msg.id} msg={msg} />
                  ))}

                  {isTyping && (
                    <motion.div
                      key="typing"
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0 }}
                      className="flex items-center gap-2 mb-3"
                    >
                      <div className="w-6 h-6 flex items-center justify-center shrink-0">
                        <img src="/baymax-logo.png" alt="Baymax" className="w-full h-full object-contain drop-shadow-md" />
                      </div>
                      <div
                        className="px-4 py-3"
                        style={{
                          background: 'rgba(255,255,255,0.08)',
                          border: '1px solid rgba(255,255,255,0.1)',
                          borderRadius: '16px',
                          borderBottomLeftRadius: '4px',
                        }}
                      >
                        <TypingIndicator />
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
                <div ref={messagesEndRef} />
              </div>

              {/* ── Input ── */}
              <div
                className="shrink-0 p-3"
                style={{ borderTop: '1px solid rgba(255,255,255,0.07)' }}
              >
                <form
                  onSubmit={handleSend}
                  className="flex items-center gap-2 px-4 py-2"
                  style={{
                    background: 'rgba(255,255,255,0.07)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: '99px',
                  }}
                >
                  <input
                    type="text"
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    placeholder="Describe your symptoms..."
                    disabled={isTyping}
                    className="flex-1 bg-transparent text-white text-sm placeholder-white/25 focus:outline-none disabled:opacity-50"
                  />
                  <button
                    type="submit"
                    disabled={!inputText.trim() || isTyping}
                    className="group w-8 h-8 flex items-center justify-center disabled:opacity-30 transition-all duration-200 hover:scale-110 active:scale-95 cursor-pointer shrink-0"
                    style={{
                      background: 'linear-gradient(135deg, #9f1239, #be185d)',
                      borderRadius: '50%',
                      boxShadow: '0 2px 10px rgba(159,18,57,0.4)',
                    }}
                  >
                    <Send size={13} className="text-white transition-transform group-hover:rotate-12" />
                  </button>
                </form>
                <p className="text-center text-white/15 text-[9px] mt-2 tracking-wide">
                  Not a substitute for professional medical advice
                </p>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

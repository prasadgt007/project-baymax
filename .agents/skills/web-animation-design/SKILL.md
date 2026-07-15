---
name: web-animation-design
description: "Use when adding or refining UI motion in the Project Baymax React frontend with Framer Motion — chat bubble entrances, panel/modal transitions, slot-chip and list animations, login→chat/dashboard phase transitions, typing indicators, staggered reveals. NOT for 3D/WebGL animation (see r3f-3d-experience) or static Tailwind styling with no motion."
metadata:
  author: baymax-project
  version: "1.0.0"
---

# Web Animation Design (Framer Motion)

## Project context
- **Framer Motion v12** (`framer-motion`) is already used in `frontend/src/App.jsx`.
- `ChatBubble` animates in with a spring (`motion.div`, initial→animate). `AnimatePresence` is
  imported. UI has four phases: `login | initializing | chat | dashboard`.
- Aim from the product spec: **fluid spring animations** that feel calm and organic (Baymax is a
  gentle healthcare companion) — not bouncy or flashy.

## Principles (most important first)
1. **Animate only `transform` and `opacity` where possible.** They're GPU-composited and won't
   trigger layout/paint. Avoid animating `width`/`height`/`top`/`left`; use `scale`/`x`/`y`.
2. **Springs for organic motion; keep them gentle.** Prefer
   `transition={{ type: 'spring', stiffness: 260–300, damping: 26–30 }}`. High damping = calm,
   no overshoot — right for a healthcare tone. Reserve tween/`ease` for precise UI (progress,
   fades).
3. **`AnimatePresence` for mount/unmount.** Wrap conditionally-rendered UI (chat messages,
   modals, toasts, the login card) so they get an `exit` animation. Requires a **stable, unique
   `key`** on each child (use message id, not array index).
4. **Reuse variants; don't inline new objects each render.** Define `variants` at module scope
   (or `useMemo`) and reference by name. Inlining a fresh object every render defeats memoization
   and can restart animations.
5. **Stagger lists** with `staggerChildren` on a parent variant for message groups or slot chips
   — feels intentional, not simultaneous.
6. **Honor reduced motion.** Use `useReducedMotion()`; when true, drop springs to near-instant
   fades and disable large translate/scale. Also gate any looping/attention animation.
7. **Use `layout` sparingly.** `layout`/`layoutId` animates position changes smoothly (e.g. a
   slot chip morphing into a confirmation), but it measures the DOM — don't put it on long
   auto-scrolling lists (chat history) where it causes reflow churn.
8. **Coordinate with the 3D scene.** The login→chat transition should feel like one motion: fade
   the login card out (Framer Motion) while the camera zooms in (see `r3f-3d-experience`), driven
   by the same `phase` state.

## Quick reference

**Gentle bubble variants (module scope):**
```jsx
const bubble = {
  hidden: { opacity: 0, y: 12, scale: 0.97 },
  show:   { opacity: 1, y: 0, scale: 1,
            transition: { type: 'spring', stiffness: 280, damping: 28 } },
  exit:   { opacity: 0, y: -6, transition: { duration: 0.15 } },
}
```

**Animated, exit-aware message list:**
```jsx
<AnimatePresence initial={false}>
  {messages.map((m) => (
    <motion.div key={m.id} variants={bubble} initial="hidden" animate="show" exit="exit">
      <ChatBubble msg={m} />
    </motion.div>
  ))}
</AnimatePresence>
```

**Reduced motion:**
```jsx
const reduce = useReducedMotion()
const t = reduce ? { duration: 0 } : { type: 'spring', stiffness: 280, damping: 28 }
```

**Staggered container:**
```jsx
const list = { show: { transition: { staggerChildren: 0.06 } } }
// <motion.div variants={list} initial="hidden" animate="show"> {chips…} </motion.div>
```

## Verify
- `cd frontend && npm run dev` and watch the actual transition (login→chat, new message,
  slot chips appearing, modal open/close).
- Toggle OS "reduce motion" and confirm animations degrade to quick fades.
- Watch the Performance panel for dropped frames during rapid message bursts.

---
name: r3f-3d-experience
description: "Use when editing Project Baymax's 3D background or camera in the React Three Fiber frontend (frontend/src/App.jsx and any extracted Scene component). Triggers: the animated background, the neural-network / node / 'blob' visuals, glowing nodes, bloom/postprocessing, camera zoom on login, mouse parallax, useFrame loops, or 3D performance/jank on laptop or mobile. NOT for plain 2D DOM/Tailwind layout or non-3D React work."
metadata:
  author: baymax-project
  version: "1.0.0"
---

# 3D Web Experience Architect (React Three Fiber)

## Project context (verify before editing)
- Stack: **React Three Fiber v9** (`@react-three/fiber`), **drei v10** (`@react-three/drei`),
  **postprocessing v3** (`@react-three/postprocessing`, installed but currently unused),
  `three ^0.185`, **React 19**, Vite 6.
- The scene lives in `frontend/src/App.jsx`: `HeroBlob` (three distorted spheres via
  `MeshDistortMaterial`) inside `Scene` (`<Canvas>`), mounted at the app root and fed a
  `mouse` ref for parallax.
- **Design goal (not yet built):** a rotating **hub-and-spoke neural network** background with
  **glowing nodes**, plus a **camera zoom triggered by login state**, smooth on **laptop and
  mobile**. The current blob is a placeholder — expect to replace/extend it.

## Golden rules (R3F footguns, most important first)
1. **Never drive per-frame changes through React state.** Rotations, positions, camera moves,
   pulsing — mutate refs inside `useFrame` (`ref.current.rotation.y += ...`). A `setState` per
   frame re-renders the React tree and tanks FPS. (Current code does this correctly with refs.)
2. **Mount the `<Canvas>` once; never remount it to change something.** Drive all changes by
   props/refs/state read inside `useFrame`. Conditionally unmounting the Canvas (e.g. per login
   phase) forces a full WebGL context teardown/rebuild — expensive and leak-prone. This is why
   the Scene should be its **own component**, mounted at the app root, receiving the login phase
   as a prop for the zoom effect.
3. **Instance repeated objects.** A neural network with many nodes must use a single
   `InstancedMesh` (drei `<Instances>`/`<Instance>`), not N `<mesh>`es — N draw calls will jank
   mobile. Edges/spokes: one `<Line>` (drei) or a single `LineSegments` BufferGeometry, not many
   cylinder meshes.
4. **Don't allocate in render or per frame.** Create geometries/materials/vectors once
   (`useMemo`, or module scope) and reuse. Allocating `new THREE.Vector3()`/colors inside
   `useFrame` churns GC and stutters. Reuse a scratch vector.
5. **Clamp DPR and scale cost for mobile.** Set `<Canvas dpr={[1, 2]}>` (never uncapped
   `devicePixelRatio` on phones). Reduce geometry detail and node counts on small screens
   (`window.matchMedia('(max-width: 768px)')`). The current spheres use `128×128` segments —
   overkill; drop to ~32–64, especially on mobile.
6. **Glow = emissive material + selective Bloom.** Use the already-installed
   `@react-three/postprocessing`: wrap effects in `<EffectComposer>` with `<Bloom>` and give
   nodes an `emissive`/`emissiveIntensity` (or `meshStandardMaterial` + high emissive). Keep
   `Bloom` intensity modest and `mipmapBlur` on; bloom is the biggest mobile GPU cost, so gate
   it down (or off) on low-end devices.
7. **Animate the camera, don't teleport it.** For login zoom, `lerp` the camera toward a target
   inside `useFrame` driven by a prop (see snippet). Avoid drei `CameraControls` unless you need
   user input — a manual lerp is lighter and deterministic.
8. **Respect `prefers-reduced-motion`.** Read it once; if set, freeze or greatly slow rotation
   and skip the breathing/pulse. Accessibility + battery.
9. **Throttle when hidden/idle.** Consider `frameloop="demand"` if the scene is static, or pause
   `useFrame` work when the tab is hidden (`document.hidden`). For a continuously animating
   background, keep `frameloop="always"` but keep per-frame work cheap.
10. **Let R3F own disposal.** Objects declared as JSX primitives are auto-disposed on unmount.
    Anything you create imperatively with `new THREE.*` (textures, geometries) must be
    `.dispose()`d in a `useEffect` cleanup.

## Structure recommendation (the "#2" fix)
Extract the 3D layer into `frontend/src/components/Scene.jsx` (or a `scene/` folder):
`Scene` owns the `<Canvas>`, takes `phase`/`mouse` props, and never unmounts. App renders it once
behind the UI. This removes the 3D code from the 943-line `App.jsx` and makes the login-zoom a
simple prop change — far more robust than any per-frame remount.

## Quick reference

**Camera zoom on login (prop-driven lerp):**
```jsx
function Rig({ zoomedIn }) {
  const target = useRef(new THREE.Vector3())
  useFrame((state, dt) => {
    target.current.set(0, 0, zoomedIn ? 4 : 7)          // closer when logged in
    state.camera.position.lerp(target.current, 1 - Math.pow(0.001, dt)) // frame-rate independent
    state.camera.lookAt(0, 0, 0)
  })
  return null
}
// <Canvas><Rig zoomedIn={phase !== 'login'} /> ... </Canvas>
```

**Instanced glowing nodes + bloom:**
```jsx
import { Instances, Instance } from '@react-three/drei'
import { EffectComposer, Bloom } from '@react-three/postprocessing'

<Instances limit={nodes.length}>
  <sphereGeometry args={[0.06, 16, 16]} />
  <meshStandardMaterial emissive="#be185d" emissiveIntensity={2} color="#9f1239" toneMapped={false} />
  {nodes.map((n, i) => <Instance key={i} position={n.pos} />)}
</Instances>

<EffectComposer disableNormalPass>
  <Bloom intensity={0.9} luminanceThreshold={0.2} mipmapBlur />
</EffectComposer>
```

**Mobile-aware Canvas:**
```jsx
<Canvas dpr={[1, 2]} gl={{ antialias: true, powerPreference: 'high-performance' }}
        camera={{ position: [0, 0, 7], fov: 50 }}>
```

## Verify your change
- `cd frontend && npm run dev`, open http://localhost:3000, watch for jank.
- Check mobile: DevTools device toolbar (or the `playwright-frontend-testing` skill) at a phone
  viewport — the background must hold a smooth frame rate and not spike memory.
- Confirm the login transition zooms the camera without the canvas flickering/remounting.

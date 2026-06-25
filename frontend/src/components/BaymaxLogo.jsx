export default function BaymaxLogo({ size = 48 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 120 120"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-label="Baymax Logo"
    >
      {/* Outer Circle — Soft Blue */}
      <circle cx="60" cy="60" r="56" fill="url(#logoGradient)" />
      <circle cx="60" cy="60" r="56" stroke="#b9dcfe" strokeWidth="2" />

      {/* Head */}
      <ellipse cx="60" cy="42" rx="22" ry="18" fill="white" />

      {/* Eyes */}
      <circle cx="52" cy="40" r="3.5" fill="#0a3c6f" />
      <circle cx="68" cy="40" r="3.5" fill="#0a3c6f" />

      {/* Eye connector line */}
      <line x1="55.5" y1="40" x2="64.5" y2="40" stroke="#0a3c6f" strokeWidth="1.5" strokeLinecap="round" />

      {/* Body */}
      <ellipse cx="60" cy="74" rx="28" ry="24" fill="white" />

      {/* Chest Circle (Health indicator) */}
      <circle cx="60" cy="70" r="6" fill="none" stroke="#0c85eb" strokeWidth="2" />

      {/* Heart inside chest */}
      <path
        d="M57.5 69C57.5 67.5 59 66.5 60 68C61 66.5 62.5 67.5 62.5 69C62.5 70.5 60 72.5 60 72.5C60 72.5 57.5 70.5 57.5 69Z"
        fill="#0c85eb"
      />

      {/* Arms */}
      <ellipse cx="30" cy="70" rx="8" ry="14" fill="white" transform="rotate(-10 30 70)" />
      <ellipse cx="90" cy="70" rx="8" ry="14" fill="white" transform="rotate(10 90 70)" />

      <defs>
        <linearGradient id="logoGradient" x1="0" y1="0" x2="120" y2="120" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#7cc0fd" />
          <stop offset="100%" stopColor="#0c85eb" />
        </linearGradient>
      </defs>
    </svg>
  )
}

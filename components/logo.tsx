export function Logo({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <rect width="32" height="32" rx="8" fill="var(--primary)" />
      <g stroke="var(--primary-foreground)" strokeWidth="1.8" strokeLinecap="round">
        <circle cx="9" cy="9" r="2.2" fill="var(--primary-foreground)" stroke="none" />
        <circle cx="9" cy="23" r="2.2" fill="var(--primary-foreground)" stroke="none" />
        <circle cx="23" cy="16" r="2.6" fill="var(--primary-foreground)" stroke="none" />
        <path d="M11 9.6 L20.6 15" />
        <path d="M11 22.4 L20.6 17" />
      </g>
    </svg>
  )
}

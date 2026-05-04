export function RecoveryRing({
  value,
  size = 200,
  stroke = 14,
  label = "RECOVERY",
}: {
  value: number; // 0-100
  size?: number;
  stroke?: number;
  label?: string;
}) {
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - value / 100);

  // Whoop-style: green ≥67, yellow 34-66, red <34
  const color =
    value >= 67
      ? "var(--color-recovery)"
      : value >= 34
      ? "var(--color-warn)"
      : "var(--color-alert)";

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--color-border)"
          strokeWidth={stroke}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ filter: `drop-shadow(0 0 8px ${color})`, transition: "stroke-dashoffset 0.6s ease" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="metric-num text-5xl font-semibold leading-none" style={{ color }}>
          {value}
        </span>
        <span className="mt-2 text-[10px] font-medium tracking-[0.25em] text-[var(--color-text-dim)]">
          {label}
        </span>
      </div>
    </div>
  );
}

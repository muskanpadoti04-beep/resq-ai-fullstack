import React, { useState } from "react";
import { Flame, Users, UserX, Truck, DoorOpen } from "lucide-react";

// Simple geometric "H" hospital icon (matches the reference's medical badge)
export function HIcon({ size = 19, color, strokeWidth = 2.2 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="18" height="18" rx="3" />
      <path d="M8.5 7.5v9M15.5 7.5v9M8.5 12h7" />
    </svg>
  );
}

// `tech: true` cards use the reference layout (icon | number / label / sub-line) and open a detail popup on click
const CARD_DEFS = [
  { key: "active_incidents", label: "Active Incident", icon: Flame, color: "var(--rq-red)", bg: "rgba(255,59,48,0.15)", border: "rgba(255,59,48,0.5)", tech: true },
  { key: "people_at_risk", label: "People at Risk", icon: Users, color: "var(--rq-amber)", bg: "rgba(255,176,32,0.15)", border: "rgba(255,176,32,0.5)", tech: true },
  { key: "potentially_trapped", label: "Potentially Trapped", icon: UserX, color: "var(--red)", bg: "rgba(239,68,68,0.15)", border: "rgba(239,68,68,0.4)", tech: true },
  { key: "active_rescue_teams", label: "Rescue Teams Active", icon: Truck, color: "var(--cyan)", bg: "rgba(34,211,238,0.15)", border: "rgba(34,211,238,0.4)", tech: true },
  { key: "available_exits", label: "Exits Available", icon: DoorOpen, color: "var(--green)", bg: "rgba(34,197,94,0.15)", border: "rgba(34,197,94,0.4)", tech: true },
  { key: "medical_support", label: "Medical Support", icon: HIcon, color: "var(--rq-cyan)", bg: "rgba(32,200,255,0.15)", border: "rgba(32,200,255,0.5)", tech: true },
];

// Sub-line: for People at Risk, "Critical" is red and "High" amber (text stays identical)
function SubLine({ cardKey, text, color }) {
  const base = { fontSize: 12.5, fontWeight: 500, marginTop: 3 };
  if (cardKey === "people_at_risk" && text.includes(" · ")) {
    const [a, b] = text.split(" · ");
    return (
      <div style={base}>
        <span style={{ color: "var(--rq-red)" }}>{a}</span>
        <span style={{ color: "rgba(234,244,255,0.6)" }}> · </span>
        <span style={{ color: "var(--rq-amber)" }}>{b}</span>
      </div>
    );
  }
  return <div style={{ ...base, color: "rgba(234,244,255,0.72)" }}>{text}</div>;
}

function TechCard({ def, value, sub, onClick }) {
  const [hover, setHover] = useState(false);
  const { key, label, icon: Icon, color, bg, border } = def;
  return (
    <button
      type="button"
      title="Click to view details"
      onClick={() => onClick && onClick(key)}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      className="glass-panel fade-in rq-tech"
      style={{
        display: "flex", alignItems: "center", gap: 14, padding: "16px", textAlign: "left",
        cursor: "pointer", width: "100%", color: "var(--rq-white)",
        borderColor: hover ? border : undefined,
        transform: hover ? "translateY(-2px)" : "none",
        boxShadow: hover ? `0 0 16px ${bg}, 0 8px 24px rgba(0,0,0,0.35)` : undefined,
        transition: "all 0.15s ease",
      }}
    >
      <div
        style={{
          width: 52, height: 52, borderRadius: 12, flexShrink: 0,
          background: bg, border: `1px solid ${border}`,
          display: "flex", alignItems: "center", justifyContent: "center",
        }}
      >
        <Icon size={24} color={color} strokeWidth={2.2} />
      </div>
      <div style={{ minWidth: 0 }}>
        <div style={{ fontSize: 30, fontWeight: 800, color, lineHeight: 1.05 }}>{value}</div>
        <div style={{ fontSize: 15, fontWeight: 700, color, marginTop: 2 }}>{label}</div>
        {sub && <SubLine cardKey={key} text={sub} color={color} />}
      </div>
    </button>
  );
}

export default function StatusCards({ summary, breakdown = {}, onCardClick }) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))",
        gap: 14,
      }}
    >
      {CARD_DEFS.map((def) => {
        const { key, label, icon: Icon, color, bg, border, tech } = def;
        const value = summary ? summary[key] : "—";
        if (tech) {
          return <TechCard key={key} def={def} value={value} sub={breakdown[key]} onClick={onCardClick} />;
        }
        return (
          <div key={key} className="glass-panel fade-in" style={{ padding: 16, display: "flex", gap: 12, alignItems: "flex-start" }}>
            <div
              style={{
                width: 40, height: 40, borderRadius: 10, flexShrink: 0,
                background: bg, border: `1px solid ${border}`,
                display: "flex", alignItems: "center", justifyContent: "center",
              }}
            >
              <Icon size={19} color={color} />
            </div>
            <div>
              <div style={{ fontSize: 24, fontWeight: 800, color: "#fff", lineHeight: 1.1 }}>{value}</div>
              <div style={{ fontSize: 11, marginTop: 3, textTransform: "uppercase", letterSpacing: "0.02em", color: "var(--text-muted)" }}>
                {label}
              </div>
              {breakdown[key] && (
                <div style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 3 }}>{breakdown[key]}</div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

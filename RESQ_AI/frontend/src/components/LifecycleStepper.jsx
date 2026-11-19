import React from "react";

const STEPS = ["Detected", "Acknowledged", "Assigned", "En Route", "On Scene", "Resolved"];

// Six circles instead of a text timeline: green = done, blinking = happening now, grey = next.
export default function LifecycleStepper({ incident }) {
  if (!incident) return null;
  const now = Math.max(STEPS.indexOf(incident.lifecycle || "Detected"), 0);
  return (
    <div className="glass-panel" style={{ padding: "14px 16px" }}>
      <div style={{ fontSize: 13, fontWeight: 700, letterSpacing: 1, marginBottom: 12 }}>RESPONSE PROGRESS</div>
      <div style={{ display: "flex", alignItems: "flex-start" }}>
        {STEPS.map((label, i) => {
          const done = i < now || (i === now && label === "Resolved");
          const current = i === now && !done;
          const colour = done ? "#30d158" : current ? "#ff9f0a" : "#4a5568";
          return (
            <div key={label} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", position: "relative" }}>
              {i > 0 && (
                <div style={{ position: "absolute", top: 13, right: "50%", width: "100%", height: 3,
                  background: i <= now ? "#30d158" : "#4a5568" }} />
              )}
              <div className={current ? "resq-blink" : ""} style={{ zIndex: 1, width: 28, height: 28, borderRadius: "50%",
                background: colour, color: "#07101c", fontWeight: 800, fontSize: 14,
                display: "flex", alignItems: "center", justifyContent: "center" }}>
                {done ? "✓" : i + 1}
              </div>
              <div style={{ fontSize: 11.5, marginTop: 6, textAlign: "center", lineHeight: 1.2,
                color: done || current ? "#fff" : "var(--text-muted)", fontWeight: current ? 700 : 400 }}>
                {label}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

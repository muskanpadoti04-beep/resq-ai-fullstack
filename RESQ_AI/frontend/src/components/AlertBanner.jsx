import React from "react";

const LIFECYCLE_TEXT = {
  Detected: "Waiting for operator",
  Acknowledged: "Acknowledged",
  Assigned: "Team assigned",
  "En Route": "Team on the way",
  "On Scene": "Team on scene",
};

// One glance: is there a fire, where, how many people, what is happening.
export default function AlertBanner({ incidents, onSelectRoom }) {
  const open = (incidents || []).filter((i) => i.status === "active");
  if (open.length === 0) {
    return (
      <div style={{ padding: "12px 18px", borderRadius: 12, background: "rgba(32,200,120,0.14)",
        border: "1px solid rgba(32,200,120,0.5)", color: "#5df0a4", fontSize: 17, fontWeight: 700 }}>
        ✔ All clear · no active fire
      </div>
    );
  }
  const top = [...open].sort((a, b) => b.risk_score - a.risk_score)[0];
  const critical = top.risk_level === "Critical";
  const colour = critical ? "#ff3b30" : "#ff9f0a";
  return (
    <div
      className={critical ? "resq-banner-fire" : ""}
      onClick={() => onSelectRoom && onSelectRoom(top.room_id)}
      style={{ cursor: "pointer", padding: "14px 20px", borderRadius: 12, background: `${colour}26`,
        border: `2px solid ${colour}`, display: "flex", alignItems: "center", gap: 18, flexWrap: "wrap" }}
    >
      <span className={critical ? "resq-blink" : ""} style={{ fontSize: 30 }}>🔥</span>
      <div style={{ flex: 1, minWidth: 220 }}>
        <div style={{ fontSize: 22, fontWeight: 800, color: colour, letterSpacing: 0.5 }}>
          FIRE · ROOM {top.room_id} · {top.risk_level.toUpperCase()}
        </div>
        <div style={{ fontSize: 15, marginTop: 2 }}>
          {top.occupants_count} {top.occupants_count === 1 ? "person" : "people"} inside · {top.temperature}°C · smoke {top.smoke_level}%
        </div>
      </div>
      <div style={{ textAlign: "right" }}>
        <div style={{ fontSize: 16, fontWeight: 700 }}>{LIFECYCLE_TEXT[top.lifecycle] || top.lifecycle}</div>
        {open.length > 1 && <div style={{ fontSize: 13, color: "var(--text-muted)" }}>+ {open.length - 1} more active incident(s)</div>}
      </div>
    </div>
  );
}

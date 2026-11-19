import React from "react";
import { SectionTitle } from "./Common.jsx";
import { Camera, CameraOff, History } from "lucide-react";

export function CameraFeeds({ cameras }) {
  return (
    <div className="glass-panel" style={{ padding: 18 }}>
      <SectionTitle>Camera Feeds</SectionTitle>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(110px, 1fr))", gap: 10 }}>
        {cameras.slice(0, 8).map((cam) => (
          <div
            key={cam.camera_id}
            style={{
              aspectRatio: "4 / 3",
              borderRadius: 8,
              background: "linear-gradient(135deg, #0a1420, #0e1d33)",
              border: "1px solid var(--border-subtle)",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: 6,
              position: "relative",
              overflow: "hidden",
            }}
          >
            {(() => {
              // device status and stream status are shown separately
              const offline = cam.status === "offline";
              const [label, color] = offline ? ["OFFLINE", "var(--orange)"]
                : cam.stream_status === "live" ? ["LIVE", "var(--red)"]
                : cam.stream_status === "no_signal" ? ["NO SIGNAL", "var(--orange)"]
                : ["SIMULATED", "var(--text-muted)"];
              return (
                <div style={{ position: "absolute", top: 6, left: 6, display: "flex", alignItems: "center", gap: 3 }}
                  title={`Device: ${cam.status} · Stream: ${cam.stream_status}`}>
                  <span style={{ width: 5, height: 5, borderRadius: "50%", background: color }} className={label === "LIVE" ? "pulse" : ""} />
                  <span style={{ fontSize: 8, fontWeight: 700, color, letterSpacing: "0.05em" }}>{label}</span>
                </div>
              );
            })()}
            {cam.status === "online" ? <Camera size={18} color="var(--text-muted)" /> : <CameraOff size={18} color="var(--orange)" />}
            <span style={{ fontSize: 9.5, color: "var(--text-muted)" }}>{cam.room_id}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function IncidentTimeline({ events }) {
  return (
    <div className="glass-panel" style={{ padding: 18 }}>
      <SectionTitle>
        <History size={14} style={{ marginRight: 6, verticalAlign: -2 }} />
        Incident Timeline
      </SectionTitle>
      <div style={{ display: "flex", flexDirection: "column", gap: 10, maxHeight: 220, overflowY: "auto" }}>
        {events.slice(0, 12).map((ev, i) => (
          <div key={i} style={{ fontSize: 12, display: "flex", gap: 8 }}>
            <span style={{ color: "var(--cyan)", fontVariantNumeric: "tabular-nums", flexShrink: 0 }}>
              {new Date(ev.timestamp).toLocaleTimeString()}
            </span>
            <span style={{ color: "var(--text-muted)" }}>{ev.event}</span>
          </div>
        ))}
        {events.length === 0 && <span style={{ fontSize: 12, color: "var(--text-muted)" }}>No timeline events yet.</span>}
      </div>
    </div>
  );
}

import React, { useEffect, useRef, useState } from "react";

const MAX_POINTS = 40;

// Remembers the last readings of every room each time the dashboard refreshes,
// and draws temperature and smoke of the selected room as a live line chart.
export default function LiveTrend({ rooms, roomId }) {
  const history = useRef({});
  const [, setTick] = useState(0);

  useEffect(() => {
    (rooms || []).forEach((r) => {
      const h = history.current[r.room_id] || (history.current[r.room_id] = []);
      h.push({ t: r.temperature, s: r.smoke_level });
      if (h.length > MAX_POINTS) h.shift();
    });
    setTick((n) => n + 1);
  }, [rooms]);

  const room = (rooms || []).find((r) => r.room_id === roomId);
  const pts = (roomId && history.current[roomId]) || [];
  const W = 300, H = 110, PAD = 6;
  const line = (key, max) =>
    pts.map((p, i) => {
      const x = PAD + (i * (W - 2 * PAD)) / Math.max(pts.length - 1, 1);
      const v = Math.min(Math.max(p[key] ?? 0, 0), max);
      return `${x.toFixed(1)},${(H - PAD - (v / max) * (H - 2 * PAD)).toFixed(1)}`;
    }).join(" ");

  return (
    <div className="glass-panel" style={{ padding: "14px 16px" }}>
      <div style={{ fontSize: 13, fontWeight: 700, letterSpacing: 1, marginBottom: 8 }}>
        LIVE SENSORS{roomId ? ` · ROOM ${roomId}` : ""}
      </div>
      {!room || pts.length < 2 ? (
        <div style={{ fontSize: 13, color: "var(--text-muted)" }}>Waiting for sensor data…</div>
      ) : (
        <>
          <div style={{ display: "flex", gap: 22, marginBottom: 6 }}>
            <div><span style={{ fontSize: 26, fontWeight: 800, color: "#ff9f0a" }}>{room.temperature ?? "–"}°C</span>
              <div style={{ fontSize: 12, color: "var(--text-muted)" }}>temperature</div></div>
            <div><span style={{ fontSize: 26, fontWeight: 800, color: "#64d2ff" }}>{room.smoke_level ?? "–"}%</span>
              <div style={{ fontSize: 12, color: "var(--text-muted)" }}>smoke</div></div>
          </div>
          <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: 110, display: "block" }}>
            <rect x="0" y="0" width={W} height={H} rx="6" fill="rgba(255,255,255,0.04)" />
            <polyline points={line("t", 150)} fill="none" stroke="#ff9f0a" strokeWidth="2.5" strokeLinejoin="round" />
            <polyline points={line("s", 100)} fill="none" stroke="#64d2ff" strokeWidth="2.5" strokeLinejoin="round" />
          </svg>
        </>
      )}
    </div>
  );
}

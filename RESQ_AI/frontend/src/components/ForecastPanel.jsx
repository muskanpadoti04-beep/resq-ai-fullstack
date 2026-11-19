import React, { useEffect, useState } from "react";
import { SectionTitle, RiskPill } from "./Common.jsx";
import { getMlForecast, getMlModelInfo } from "../api/client.js";

const pct = (p) => `${Math.round(p * 100)}%`;

// Observed risk (rule engine, what the sensors say NOW) and ML forecast (what may happen in the
// next N minutes) are deliberately shown as two separate things.
export default function ForecastPanel({ refreshKey, onSelectRoom }) {
  const [forecasts, setForecasts] = useState(null);
  const [info, setInfo] = useState(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let off = false;
    getMlForecast()
      .then((d) => { if (!off) { setForecasts(d.forecasts); setFailed(false); } })
      .catch(() => { if (!off) setFailed(true); });
    return () => { off = true; };
  }, [refreshKey]);

  useEffect(() => {
    getMlModelInfo().then(setInfo).catch(() => {});
  }, []);

  const rows = (forecasts || [])
    .filter((f) => f.available)
    .sort((a, b) => b.probability - a.probability)
    .slice(0, 3);
  const unavailable = (forecasts || []).filter((f) => !f.available).length;

  return (
    <div className="glass-panel" style={{ padding: 16 }} data-testid="forecast-panel">
      <SectionTitle>ML Forecast · next {info?.horizon_minutes ?? 10} min</SectionTitle>
      <div style={{ fontSize: 11, color: "var(--text-muted)", margin: "-4px 0 10px" }}>
        Experimental · trained on simulated data{info?.model_version ? ` · ${info.model_version}` : ""}. Observed risk = rule engine, unchanged.
      </div>

      {failed && <div style={{ fontSize: 12, color: "#ffb020" }}>Forecast unavailable (backend did not return one).</div>}
      {!forecasts && !failed && <div style={{ fontSize: 12, color: "var(--text-muted)" }}>Loading forecast...</div>}

      {rows.map((f) => (
        <div key={f.room_id} onClick={() => onSelectRoom && onSelectRoom(f.room_id)}
          style={{ cursor: "pointer", padding: "7px 0", borderTop: "1px solid rgba(255,255,255,0.05)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 12.5 }}>
            <strong>{f.room_id}</strong>
            <span style={{ display: "flex", gap: 6, alignItems: "center" }}>
              <span style={{ color: "var(--text-muted)", fontSize: 11 }}>Observed</span>
              <RiskPill level={f.observed_risk_level} />
            </span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 5 }}>
            <span style={{ fontSize: 11, color: "var(--text-muted)", width: 52 }}>Forecast</span>
            <div style={{ flex: 1, height: 6, borderRadius: 3, background: "rgba(255,255,255,0.08)", overflow: "hidden" }}>
              <div style={{ width: pct(f.probability), height: "100%", background: f.flagged ? "#ff3b30" : "#20c8ff" }} />
            </div>
            <span style={{ fontSize: 12, fontWeight: 700, width: 38, textAlign: "right", color: f.flagged ? "#ff3b30" : undefined }}>
              {pct(f.probability)}
            </span>
          </div>
          {f.flagged && (f.observed_score > 60
            ? <div style={{ fontSize: 11, color: "#ff3b30", marginTop: 3 }}>Already {f.observed_risk_level} now — forecast expects it to stay high</div>
            : <div style={{ fontSize: 11, color: "#ff3b30", marginTop: 3 }}>⚠ May reach High Risk within {f.horizon_minutes} min</div>)}
          {f.trend_available === false && <div style={{ fontSize: 10.5, color: "var(--text-muted)", marginTop: 2 }}>No recent trend data — less reliable</div>}
        </div>
      ))}

      {forecasts && rows.length === 0 && !failed && (
        <div style={{ fontSize: 12, color: "var(--text-muted)" }}>No rooms with fresh sensor data to forecast.</div>
      )}
      {unavailable > 0 && <div style={{ fontSize: 11, color: "#ffb020", marginTop: 6 }}>{unavailable} room(s) skipped: sensor data stale or missing.</div>}
    </div>
  );
}
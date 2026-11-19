import React, { useEffect, useState } from "react";
import { getRescueRoute } from "../api/client.js";

const FLOOR_NAME = { 1: "Ground floor", 2: "1st floor", 3: "2nd floor", 4: "3rd floor" };
const MONO = "ui-monospace, 'JetBrains Mono', Consolas, 'Courier New', monospace";
const SEV_COLOUR = { Critical: "#ff5a4f", High: "#ff9f0a", Moderate: "#ffd60a", Low: "#30d158" };

// Backend times are UTC without a "Z"; add it so the browser shows the user's local time.
const toDate = (s) => (s ? new Date(/Z$|[+-]\d\d:?\d\d$/.test(s) ? s : `${s}Z`) : null);
const clock = (s) => { const d = toDate(s); return d ? d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "–"; };

function Cell({ label, children, style }) {
  return (
    <div style={{ background: "rgba(2,14,28,0.75)", border: "1px solid #10314f", borderRadius: 8, padding: "10px 12px", ...style }}>
      <div style={{ fontSize: 11.5, color: "#9fb4c8", textTransform: "uppercase", letterSpacing: 0.3 }}>{label}</div>
      <div style={{ fontFamily: MONO, fontWeight: 700, fontSize: 15, marginTop: 6, color: "#fff", lineHeight: 1.35 }}>{children}</div>
    </div>
  );
}

const btn = (colour) => ({
  background: "#031a30", color: colour || "#fff", border: `1px solid ${colour || "#12527d"}`, borderRadius: 8,
  padding: "10px 16px", fontWeight: 700, fontSize: 14, cursor: "pointer", fontFamily: "inherit",
});

// Pop-up with everything about one incident. Every value comes from the backend.
export default function IncidentModal({ incident, occupants, teams, onClose, onAcknowledge, onResolve, canAct, initialRoute, allIncidents, onSwitch }) {
  const [route, setRoute] = useState(initialRoute || null);
  const [showPeople, setShowPeople] = useState(false);
  const roomId = incident ? incident.room_id : null;

  useEffect(() => {
    if (!roomId) return undefined;
    let off = false;
    getRescueRoute(roomId).then((r) => { if (!off) setRoute(r); }).catch(() => { if (!off) setRoute({ found: false }); });
    return () => { off = true; };
  }, [roomId, incident && incident.lifecycle]);

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  if (!incident) return null;

  const people = (occupants || []).filter((o) => o.room_id === incident.room_id && !o.is_rescued);
  const atRisk = people.filter((o) => o.is_trapped || o.risk_status === "Critical" || o.risk_status === "High Risk");
  const trapped = people.filter((o) => o.is_trapped).length;
  const team = (teams || []).find((t) => t.team_id === incident.assigned_team_id)
    || (teams || []).find((t) => t.assigned_room === incident.room_id);

  const zones = [incident.room_id];
  if (route && route.found) {
    route.path.forEach((s) => { if (s.hazard && s.type !== "room" && !zones.includes(s.label)) zones.push(s.label); });
  }
  const blocked = route ? (route.blocked_exits || []) : null;
  const sevColour = SEV_COLOUR[incident.severity] || "#fff";
  const others = (allIncidents || []).filter((i) => i.incident_id !== incident.incident_id);

  return (
    <div onClick={onClose} style={{ position: "fixed", inset: 0, zIndex: 1000, background: "rgba(0,5,12,0.78)",
      backdropFilter: "blur(3px)", display: "flex", justifyContent: "center", alignItems: "flex-start", padding: "52px 16px", overflowY: "auto" }}>
      <div onClick={(e) => e.stopPropagation()} role="dialog" aria-label={`Incident ${incident.incident_id}`}
        style={{ width: "min(1180px, 100%)", background: "linear-gradient(#031a30, #021223)", border: "1px solid #12527d",
          borderRadius: 12, boxShadow: "0 20px 60px rgba(0,0,0,0.6)" }}>

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", padding: "22px 24px 18px", borderBottom: "1px solid #0f2e4b" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, fontFamily: MONO, fontSize: 12, letterSpacing: 1.5, color: "#ff3b30" }}>
              <span style={{ width: 9, height: 9, borderRadius: "50%", background: "#ff3b30" }} /> RESQ AI
            </div>
            <div style={{ fontSize: 30, fontWeight: 400, color: "#fff", marginTop: 8 }}>Incident {incident.incident_id}</div>
            <div style={{ fontSize: 14.5, color: "#9fb4c8", marginTop: 8 }}>
              Room {incident.room_id} · {FLOOR_NAME[incident.floor] || `Floor ${incident.floor}`}
            </div>
          </div>
          <button onClick={onClose} aria-label="Close" style={{ ...btn(), padding: "12px 15px", fontSize: 18, lineHeight: 1 }}>✕</button>
        </div>

        <div style={{ padding: 22 }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: 12 }}>
            <Cell label="Severity"><span style={{ color: sevColour }}>{incident.severity}</span></Cell>
            <Cell label="Detected">{clock(incident.detected_at)} · sensor network</Cell>
            <Cell label="Risk score">{incident.risk_score} / 100 · {incident.risk_level}</Cell>

            <Cell label="Temperature / smoke">{incident.temperature}°C · smoke {incident.smoke_level}%</Cell>
            <Cell label="Occupants at risk">
              {atRisk.length}{trapped > 0 ? ` (${trapped} trapped)` : ""}
              <span style={{ color: "#9fb4c8", fontWeight: 400 }}> · {people.length} in room</span>
            </Cell>
            <Cell label="Affected zones">{zones.join(", ")}</Cell>

            <Cell label="Blocked exits">
              {blocked === null ? "checking…" : blocked.length === 0 ? "None" : blocked.map((b) => b.label).join(", ")}
            </Cell>
            <Cell label="Teams">{team ? `${team.team_name} · ${team.status}${team.eta_minutes ? ` (ETA ${team.eta_minutes} min)` : ""}` : "No team assigned yet"}</Cell>
            <Cell label="Progress">{incident.lifecycle}</Cell>
          </div>

          {route && route.found && (
            <div style={{ marginTop: 12, fontSize: 13.5, color: "#9fb4c8" }}>
              Rescue route: <span style={{ color: "#fff" }}>{route.entrance}</span> → Room {incident.room_id} · {route.distance_m} m · about {route.estimated_seconds} s
              {route.through_hazard ? <span style={{ color: "#ff9f0a" }}> · passes through hazard</span> : null}
            </div>
          )}

          <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginTop: 16 }}>
            <button onClick={() => setShowPeople((v) => !v)} style={btn()}>{showPeople ? "Hide room occupants" : "Open room occupants"}</button>
            {canAct && incident.lifecycle === "Detected" && onAcknowledge && (
              <button onClick={() => onAcknowledge(incident.incident_id)} style={btn("#ff9f0a")}>Acknowledge</button>
            )}
            {canAct && onResolve && (
              <button onClick={() => onResolve(incident.incident_id)} style={btn("#30d158")}>Resolve incident</button>
            )}
          </div>

          {showPeople && (
            <div style={{ marginTop: 14, border: "1px solid #10314f", borderRadius: 8, overflow: "hidden" }}>
              {people.length === 0 ? (
                <div style={{ padding: 12, color: "#9fb4c8", fontSize: 14 }}>No one left in this room.</div>
              ) : people.map((o) => (
                <div key={o.occupant_id} style={{ display: "flex", justifyContent: "space-between", gap: 10, padding: "9px 12px", borderTop: "1px solid #0f2e4b", fontSize: 14 }}>
                  <span><strong>{o.name}</strong> <span style={{ color: "#9fb4c8" }}>· {o.type}{o.type === "Human" ? ` · ${o.age_group}` : ""}</span></span>
                  <span style={{ fontWeight: 700, color: o.is_trapped ? "#ff5a4f" : o.risk_status === "Safe" ? "#30d158" : "#ff9f0a" }}>
                    {o.is_trapped ? "Trapped" : o.risk_status}
                  </span>
                </div>
              ))}
            </div>
          )}

          {others.length > 0 && onSwitch && (
            <div style={{ marginTop: 18 }}>
              <div style={{ fontSize: 11.5, color: "#9fb4c8", textTransform: "uppercase", letterSpacing: 0.3, marginBottom: 6 }}>
                Other active incidents ({others.length})
              </div>
              <div style={{ border: "1px solid #10314f", borderRadius: 8, overflow: "hidden", maxHeight: 190, overflowY: "auto" }}>
                {others.map((i) => (
                  <button key={i.incident_id} onClick={() => onSwitch(i.incident_id)}
                    style={{ display: "flex", width: "100%", justifyContent: "space-between", alignItems: "center", gap: 10, padding: "9px 12px",
                      background: "transparent", color: "#fff", border: "none", borderTop: "1px solid #0f2e4b", cursor: "pointer", fontSize: 14, fontFamily: "inherit", textAlign: "left" }}>
                    <span style={{ fontFamily: MONO, fontWeight: 700 }}>Room {i.room_id}</span>
                    <span style={{ color: "#9fb4c8" }}>{clock(i.detected_at)} · {i.lifecycle}</span>
                    <span style={{ fontWeight: 700, color: SEV_COLOUR[i.severity] || "#fff" }}>{i.risk_level} · {i.risk_score}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

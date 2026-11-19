import React, { useState } from "react";
import { RiskPill, SectionTitle, fmtNum } from "./Common.jsx";
import LifecycleStepper from "./LifecycleStepper.jsx";
import IncidentDetailModal from "./IncidentDetailModal.jsx";
import { useAuth, can } from "./AuthContext.jsx";
import {
  AlertOctagon, CheckCheck, TrendingUp, DoorOpen, Layers, Users, AlertTriangle,
  Thermometer, Wind, Flame, Gauge, Maximize2,
} from "lucide-react";

// Status colors (defined by the scoped .rq-tech class in index.css)
const RED = "var(--rq-red)";
const AMBER = "var(--rq-amber)";
const CYAN = "var(--rq-cyan)";
const GREEN = "var(--rq-green)";
const WHITE = "var(--rq-white)";

const levelColor = (level) =>
  ({ Critical: RED, "High Risk": AMBER, Moderate: CYAN, Safe: GREEN }[level] || WHITE);
const severityColor = (sev) =>
  ({ Critical: RED, High: AMBER, Moderate: CYAN, Low: GREEN }[sev] || WHITE);
const tempColor = (t) => (t >= 60 ? RED : t >= 40 ? AMBER : GREEN);
const smokeColor = (s) => (s >= 60 ? RED : s >= 30 ? AMBER : GREEN);
const fireColor = (f) => ({ active: RED, smoke: AMBER, contained: AMBER, none: GREEN }[f] || WHITE);

// onOpenOccupants(roomId) and details are optional. Without onOpenOccupants the popup hides that button.
export default function ActiveIncidentPanel({ incident, onAcknowledge, onResolve, onOpenOccupants, details }) {
  const { role } = useAuth();
  const canOperate = can(role, "operator");
  const [showDetails, setShowDetails] = useState(false);

  if (!incident) {
    return (
      <div className="glass-panel rq-tech" style={{ padding: 18 }}>
        <SectionTitle>Active Incident</SectionTitle>
        <p style={{ color: "var(--text-muted)", fontSize: 13 }}>
          No incident selected. Choose a highlighted room on the map to inspect it.
        </p>
      </div>
    );
  }

  const scoreColor = levelColor(incident.risk_level);

  return (
    <>
      <div
        className="glass-panel fade-in rq-tech"
        style={{ padding: 18, cursor: "pointer" }}
        onClick={() => setShowDetails(true)}
        title="Click for full incident details"
      >
        <SectionTitle
          right={
            incident.lifecycle === "Resolved" ? (
              <span className="pill pill-safe">Resolved</span>
            ) : incident.lifecycle === "Detected" ? (
              <button className="btn" disabled={!canOperate} title={canOperate ? "" : "Operator access required"}
                      onClick={(e) => { e.stopPropagation(); onAcknowledge(incident.incident_id); }}>
                <CheckCheck size={13} style={{ marginRight: 4, verticalAlign: -2 }} />
                Acknowledge
              </button>
            ) : (
              <span className="pill pill-safe" style={{ whiteSpace: "nowrap" }}>{incident.lifecycle}</span>
            )
          }
        >
          <AlertOctagon size={14} strokeWidth={2.2} style={{ marginRight: 6, verticalAlign: -2 }} color={RED} />
          Active Incident — {incident.incident_id}
        </SectionTitle>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: -6, marginBottom: 10 }}>
          <span style={{ fontSize: 10.5, color: "rgba(234,244,255,0.65)" }}>
            Updated {new Date().toLocaleTimeString()}
          </span>
          {/* keyboard-friendly way to open the same popup */}
          <button
            className="btn"
            style={{ padding: "3px 8px", fontSize: 11 }}
            onClick={(e) => { e.stopPropagation(); setShowDetails(true); }}
          >
            <Maximize2 size={11} style={{ marginRight: 4, verticalAlign: -1 }} />
            View details
          </button>
        </div>

        <LifecycleStepper incident={incident} />

        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 10, fontSize: 12.5 }}>
          <Field label="Room" value={incident.room_id} icon={DoorOpen} color={WHITE} iconColor={CYAN} />
          <Field label="Floor" value={incident.floor} icon={Layers} color={WHITE} iconColor={CYAN} />
          <Field label="Occupants" value={incident.occupants_count} icon={Users} color={WHITE} iconColor={CYAN} />
          <Field label="Severity" value={incident.severity} icon={AlertTriangle} color={severityColor(incident.severity)} />
          <Field label="Temperature" value={fmtNum(incident.temperature, 1, "°C")} icon={Thermometer} color={tempColor(incident.temperature)} />
          <Field label="Smoke Level" value={fmtNum(incident.smoke_level, 0, "%")} icon={Wind} color={smokeColor(incident.smoke_level)} />
          <Field label="Fire Status" value={incident.fire_status} icon={Flame} color={fireColor(incident.fire_status)} />
          <Field label="Risk Score" value={`${incident.risk_score.toFixed(1)} / 100`} icon={Gauge} color={scoreColor} />
        </div>

        {canOperate && incident.lifecycle !== "Resolved" && onResolve && (
          <button className="btn" style={{ marginTop: 12, width: "100%" }}
                  onClick={(e) => { e.stopPropagation(); onResolve(incident.incident_id); }}>
            Resolve incident (fire out / false alarm)
          </button>
        )}

        <div style={{ marginTop: 14, display: "flex", alignItems: "center", gap: 8 }}>
          <RiskPill level={incident.risk_level} />
          <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
            Detected {new Date(incident.detected_at).toLocaleTimeString()}
          </span>
        </div>

        <div style={{ marginTop: 16, paddingTop: 14, borderTop: "1px solid var(--border-subtle)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, fontWeight: 800, color: RED, marginBottom: 6, letterSpacing: "0.02em" }}>
            <AlertTriangle size={14} strokeWidth={2.2} />
            Why Priority #1?
          </div>
          <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12.5, color: "rgba(234,244,255,0.72)", lineHeight: 1.7 }}>
            <li>Risk score of {incident.risk_score.toFixed(1)} classified as {incident.risk_level} by the RESQ AI risk engine</li>
            <li>{incident.occupants_count} occupant(s) in the affected zone</li>
            <li>Fire status: {incident.fire_status}</li>
          </ul>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginTop: 14 }}>
          <div className="glass-panel" style={{ padding: 10 }}>
            <div style={{ fontSize: 9.5, fontWeight: 600, color: "rgba(234,244,255,0.72)", textTransform: "uppercase", letterSpacing: "0.03em" }}>Risk Trend</div>
            <div style={{ display: "flex", alignItems: "center", gap: 4, color: RED, fontWeight: 800, fontSize: 13 }}>
              <TrendingUp size={14} strokeWidth={2.2} /> Increasing
            </div>
          </div>
          <div className="glass-panel" style={{ padding: 10 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 9.5, fontWeight: 600, color: "rgba(234,244,255,0.72)", textTransform: "uppercase", letterSpacing: "0.03em" }}>
              <Gauge size={11} strokeWidth={2.2} color={scoreColor} />
              Priority Score
            </div>
            <div style={{ fontWeight: 800, fontSize: 18, lineHeight: 1.15, color: scoreColor }}>
              {incident.risk_score.toFixed(0)} <span style={{ fontSize: 10, color: "rgba(234,244,255,0.6)", fontWeight: 500 }}>/ 100</span>
            </div>
          </div>
        </div>
      </div>

      {/* Sibling of the panel (not a child), so clicks inside the popup never re-trigger the panel's onClick. */}
      <IncidentDetailModal
        incident={showDetails ? incident : null}
        details={details}
        onClose={() => setShowDetails(false)}
        onOpenOccupants={
          onOpenOccupants
            ? (roomId) => { setShowDetails(false); onOpenOccupants(roomId); }
            : undefined
        }
      />
    </>
  );
}

// [icon] label / value, colored by status
function Field({ label, value, icon: Icon, color = WHITE, iconColor }) {
  return (
    <div>
      <div
        style={{
          display: "flex", alignItems: "center", gap: 5,
          color: "rgba(234,244,255,0.72)", fontSize: 10.5, fontWeight: 600,
          textTransform: "uppercase", letterSpacing: "0.03em",
        }}
      >
        {Icon && <Icon size={12} strokeWidth={2.2} color={iconColor || color} />}
        {label}
      </div>
      <div style={{ fontWeight: 800, fontSize: 14, color }}>{value}</div>
    </div>
  );
}

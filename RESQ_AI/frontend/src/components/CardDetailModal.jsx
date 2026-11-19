import React, { useEffect, useState } from "react";
import { X, Flame, Users, User, PawPrint, Ambulance } from "lucide-react";
import { RiskPill } from "./Common.jsx";
import { HIcon } from "./StatusCards.jsx";
import IncidentDetailModal from "./IncidentDetailModal.jsx";

// Popup opened by clicking the Active Incident / People at Risk / Medical Support cards
const META = {
  active_incidents: { title: "Active Incidents", color: "var(--rq-red)", bg: "rgba(255,59,48,0.15)", border: "rgba(255,59,48,0.5)", glow: "rgba(255,59,48,0.35)" },
  people_at_risk: { title: "People at Risk", color: "var(--rq-amber)", bg: "rgba(255,176,32,0.15)", border: "rgba(255,176,32,0.5)", glow: "rgba(255,176,32,0.3)" },
  medical_support: { title: "Medical Support", color: "var(--rq-cyan)", bg: "rgba(32,200,255,0.15)", border: "rgba(32,200,255,0.5)", glow: "rgba(32,200,255,0.3)" },
};
const MED_COLOR = { "En Route": "var(--rq-cyan)", "On Scene": "var(--rq-cyan)", Standby: "var(--rq-green)" };

const th = {
  textAlign: "left", padding: "8px 10px", fontSize: 11, fontWeight: 600, textTransform: "uppercase",
  letterSpacing: "0.04em", color: "rgba(234,244,255,0.65)", borderBottom: "1px solid var(--border-subtle)",
};
const td = { padding: "10px", fontSize: 13.5, borderBottom: "1px solid rgba(255,255,255,0.05)" };
const linkBtn = {
  background: "rgba(32,200,255,0.12)", border: "1px solid rgba(32,200,255,0.4)", color: "var(--rq-cyan)",
  borderRadius: 6, padding: "3px 10px", fontSize: 12, fontWeight: 700, cursor: "pointer", whiteSpace: "nowrap",
};

function Empty({ text }) {
  return <div style={{ padding: 24, color: "rgba(234,244,255,0.65)", fontSize: 13.5 }}>{text}</div>;
}

// Row click opens the single-incident popup; the "Show on map" button still just highlights the room.
function IncidentsTable({ incidents, onSelectRoom, onSelectIncident }) {
  if (!incidents.length) return <Empty text="No active incidents." />;
  return (
    <table style={{ width: "100%", borderCollapse: "collapse" }}>
      <thead>
        <tr>{["Incident", "Room", "Floor", "Risk", "Score", "Detected", ""].map((h) => <th key={h} style={th}>{h}</th>)}</tr>
      </thead>
      <tbody>
        {incidents.map((i) => (
          <tr key={i.incident_id} onClick={() => onSelectIncident(i.incident_id)} style={{ cursor: "pointer" }}
              title="Click for full incident details">
            <td style={{ ...td, fontWeight: 700 }}>{i.incident_id}</td>
            <td style={td}>{i.room_id}</td>
            <td style={td}>{i.floor}</td>
            <td style={td}><RiskPill level={i.risk_level} /></td>
            <td style={{ ...td, fontWeight: 800, color: "var(--rq-red)" }}>{i.risk_score.toFixed(1)}</td>
            <td style={{ ...td, color: "rgba(234,244,255,0.72)" }}>{new Date(i.detected_at).toLocaleTimeString()}</td>
            <td style={td}><button style={linkBtn} onClick={(e) => { e.stopPropagation(); onSelectRoom(i.room_id); }}>Show on map</button></td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function PeopleTable({ people, onSelectRoom }) {
  if (!people.length) return <Empty text="Nobody is currently at risk." />;
  return (
    <table style={{ width: "100%", borderCollapse: "collapse" }}>
      <thead>
        <tr>{["Type", "Room", "Status", "Trapped", ""].map((h) => <th key={h} style={th}>{h}</th>)}</tr>
      </thead>
      <tbody>
        {people.map((o) => (
          <tr key={o.occupant_id} onClick={() => onSelectRoom(o.room_id)} style={{ cursor: "pointer" }}>
            <td style={{ ...td, fontWeight: 700 }}>
              <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                {o.type === "Dog" ? <PawPrint size={14} color="var(--rq-amber)" /> : <User size={14} color="var(--rq-cyan)" />}
                {o.type === "Dog" ? "Animal" : "Person"}
              </span>
            </td>
            <td style={td}>{o.room_id}</td>
            <td style={td}><RiskPill level={o.risk_status} /></td>
            <td style={{ ...td, fontWeight: 700, color: o.is_trapped ? "var(--rq-red)" : "rgba(234,244,255,0.72)" }}>{o.is_trapped ? "Yes" : "No"}</td>
            <td style={td}><button style={linkBtn} onClick={(e) => { e.stopPropagation(); onSelectRoom(o.room_id); }}>Show on map</button></td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function MedicalContent({ units, onSelectRoom }) {
  return (
    <>
      {!units.length ? (
        <Empty text="No medical units available." />
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>{["Unit", "Status", "Personnel", "ETA", "Assigned room", ""].map((h) => <th key={h} style={th}>{h}</th>)}</tr>
          </thead>
          <tbody>
            {units.map((u) => {
              const c = MED_COLOR[u.status] || "rgba(234,244,255,0.72)";
              return (
                <tr key={u.unit_id} onClick={() => u.assigned_room && onSelectRoom(u.assigned_room)} style={{ cursor: u.assigned_room ? "pointer" : "default" }}>
                  <td style={{ ...td, fontWeight: 700 }}>
                    <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                      <Ambulance size={15} strokeWidth={2.2} color={c} />
                      {u.unit_name}
                    </span>
                  </td>
                  <td style={{ ...td, fontWeight: 800, color: c }}>{u.status}</td>
                  <td style={td}>{u.personnel_count}</td>
                  <td style={td}>{u.eta_minutes ? `${u.eta_minutes} min` : "—"}</td>
                  <td style={td}>{u.assigned_room || "—"}</td>
                  <td style={td}>
                    {u.assigned_room && (
                      <button style={linkBtn} onClick={(e) => { e.stopPropagation(); onSelectRoom(u.assigned_room); }}>Show on map</button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
      <div className="glass-panel" style={{ margin: 14, padding: 12, borderColor: "rgba(32,200,255,0.35)" }}>
        <div style={{ fontSize: 10.5, fontWeight: 600, color: "rgba(234,244,255,0.72)", textTransform: "uppercase", letterSpacing: "0.03em", marginBottom: 4 }}>
          Recommended Hospital
        </div>
        <div style={{ fontWeight: 800, fontSize: 15 }}>City General Hospital</div>
        <div style={{ display: "flex", gap: 6, marginTop: 6, flexWrap: "wrap" }}>
          {["Trauma Care", "Burn Unit", "Emergency"].map((t) => (
            <span key={t} className="pill pill-safe" style={{ fontSize: 10 }}>{t} ✓</span>
          ))}
        </div>
        <div style={{ fontSize: 12, color: "rgba(234,244,255,0.72)", marginTop: 8 }}>2.4 km · ETA ~6 min</div>
      </div>
    </>
  );
}

// onOpenOccupants(roomId) is optional. Without it, the single-incident popup hides its "Open room occupants" button.
export default function CardDetailModal({ type, incidents, occupants, medical, onClose, onSelectRoom, onOpenOccupants }) {
  const [selectedId, setSelectedId] = useState(null);
  const selectedIncident = selectedId ? incidents.find((i) => i.incident_id === selectedId) || null : null;

  useEffect(() => {
    const onKey = (e) => {
      // while the single-incident popup is open, Esc closes only that popup (it handles its own Esc)
      if (e.key === "Escape" && !selectedId) onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, selectedId]);

  const meta = META[type];
  if (!meta) return null;

  const order = { Critical: 0, "High Risk": 1 };
  const people = occupants
    .filter((o) => !o.is_rescued && (o.risk_status === "Critical" || o.risk_status === "High Risk"))
    .sort((a, b) => order[a.risk_status] - order[b.risk_status] || a.name.localeCompare(b.name));
  const criticalCount = people.filter((p) => p.risk_status === "Critical").length;

  const subtitle =
    type === "active_incidents" ? `${incidents.length} active`
    : type === "people_at_risk" ? `${people.length} people · ${criticalCount} critical`
    : `${medical.length} units`;
  const Icon = type === "active_incidents" ? Flame : type === "people_at_risk" ? Users : HIcon;

  return (
    <>
      <div
        onClick={onClose}
        style={{
          position: "fixed", inset: 0, zIndex: 200, display: "flex", alignItems: "center", justifyContent: "center",
          background: "rgba(3,8,16,0.72)", backdropFilter: "blur(3px)", padding: 16,
        }}
      >
        <div
          className="glass-panel rq-tech fade-in"
          onClick={(e) => e.stopPropagation()}
          style={{
            width: "min(760px, 94vw)", maxHeight: "80vh", display: "flex", flexDirection: "column",
            borderColor: meta.border, boxShadow: `0 0 28px ${meta.glow}, 0 16px 48px rgba(0,0,0,0.6)`,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 14, padding: "16px 18px", borderBottom: "1px solid var(--border-subtle)" }}>
            <div
              style={{
                width: 44, height: 44, borderRadius: 10, background: meta.bg, border: `1px solid ${meta.border}`,
                display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
              }}
            >
              <Icon size={22} color={meta.color} strokeWidth={2.2} />
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 20, fontWeight: 800, color: meta.color, lineHeight: 1.1 }}>{meta.title}</div>
              <div style={{ fontSize: 13, color: "rgba(234,244,255,0.72)", marginTop: 2 }}>{subtitle}</div>
            </div>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close"
              style={{
                background: "transparent", border: "1px solid var(--border-subtle)", color: "var(--rq-white)",
                borderRadius: 8, width: 32, height: 32, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center",
              }}
            >
              <X size={16} />
            </button>
          </div>
          <div style={{ overflowY: "auto" }}>
            {type === "active_incidents" && (
              <IncidentsTable incidents={incidents} onSelectRoom={onSelectRoom} onSelectIncident={setSelectedId} />
            )}
            {type === "people_at_risk" && <PeopleTable people={people} onSelectRoom={onSelectRoom} />}
            {type === "medical_support" && <MedicalContent units={medical} onSelectRoom={onSelectRoom} />}
          </div>
        </div>
      </div>

      {/* Sibling of the list popup (not a child), so closing it never closes the list underneath. */}
      <IncidentDetailModal
        incident={selectedIncident}
        onClose={() => setSelectedId(null)}
        onOpenOccupants={
          onOpenOccupants
            ? (roomId) => { setSelectedId(null); onClose(); onOpenOccupants(roomId); }
            : undefined
        }
      />
    </>
  );
}

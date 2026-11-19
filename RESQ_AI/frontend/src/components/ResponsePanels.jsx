import React, { useState } from "react";
import { Truck, Hospital, Ambulance } from "lucide-react";
import { PanelHeader, DetailDrawer, DrawerRow, muted } from "./PanelKit.jsx";

// Backend status -> label + colour shown in the panel
const TEAM_STATUS = {
  "On Scene": { label: "On Site", color: "#3b9cff" },
  "En Route": { label: "En Route", color: "#20c8ff" },
  Standby: { label: "Available", color: "#22e6a3" },
};
const teamStatus = (s) => TEAM_STATUS[s] || { label: s || "Unknown", color: "rgba(234,244,255,0.6)" };
const etaOf = (t) => {
  const v = t.eta_minutes ?? t.eta_min ?? t.eta;
  return v === undefined || v === null || v === "" ? null : typeof v === "number" ? `${v} min` : String(v);
};

export function RescueTeamsPanel({ teams, highlightTeamId = null }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="glass-panel rq-tech" style={{ padding: 16 }}>
      <PanelHeader icon={Truck} title="Rescue Teams" actionLabel="View All" onAction={() => setOpen(true)} />

      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {teams.map((t) => {
          const st = teamStatus(t.status);
          const highlighted = t.team_id === highlightTeamId;
          return (
            <div
              key={t.team_id}
              style={{
                display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10,
                padding: "10px 12px", borderRadius: 8,
                border: `1px solid ${highlighted ? "var(--rq-cyan)" : "var(--border-subtle)"}`,
                background: highlighted ? "rgba(32,200,255,0.10)" : "rgba(14,29,51,0.6)",
                boxShadow: highlighted ? "0 0 12px rgba(32,200,255,0.25)" : "none",
              }}
            >
              <div style={{ minWidth: 0 }}>
                <div style={{ fontWeight: 700, fontSize: 17, color: "var(--rq-white)" }}>{t.team_name}</div>
                <div style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 12, color: st.color, marginTop: 2 }}>
                  <span style={{ width: 6, height: 6, borderRadius: "50%", background: st.color }} />
                  {st.label}
                </div>
              </div>
              <div style={{ textAlign: "right", fontSize: 12, color: "rgba(234,244,255,0.7)", flexShrink: 0 }}>
                <div>{t.assigned_room || "At Base"}</div>
                <div>{etaOf(t) || "—"}</div>
              </div>
            </div>
          );
        })}
        {teams.length === 0 && <div style={muted}>No rescue teams on the roster.</div>}
      </div>

      <DetailDrawer open={open} onClose={() => setOpen(false)} title="Rescue Teams" icon={Truck}>
        {teams.map((t) => {
          const st = teamStatus(t.status);
          return (
            <DrawerRow key={t.team_id} accent={t.team_id === highlightTeamId ? "var(--rq-cyan)" : undefined}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div style={{ fontWeight: 700, fontSize: 16, color: "var(--rq-white)" }}>{t.team_name}</div>
                <span style={{ color: st.color, fontWeight: 700 }}>{st.label}</span>
              </div>
              <div style={{ ...muted, marginTop: 6, display: "grid", gap: 3 }}>
                <span>Location: {t.current_location || "—"}</span>
                <span>Assigned room: {t.assigned_room || "None"}</span>
                <span>ETA: {etaOf(t) || "—"}</span>
                {t.personnel_count !== undefined && <span>Personnel: {t.personnel_count}</span>}
              </div>
            </DrawerRow>
          );
        })}
      </DetailDrawer>
    </div>
  );
}

export function MedicalPanel({ units }) {
  const [open, setOpen] = useState(false);
  const assigned = units.filter((u) => u.status !== "Standby").length;

  const hospitalTags = ["Trauma Care", "Burn Unit", "Emergency"];
  const tagStyle = {
    fontSize: 10.5, fontWeight: 600, padding: "2px 8px", borderRadius: 6,
    border: "1px solid rgba(32,200,255,0.45)", background: "rgba(32,200,255,0.08)", color: "var(--rq-cyan)",
  };

  return (
    <div className="glass-panel rq-tech" style={{ padding: 16 }}>
      <PanelHeader icon={Hospital} title="Medical & Hospital" onAction={() => setOpen(true)} />

      <div
        style={{
          display: "flex", alignItems: "center", gap: 14, padding: "14px 14px", borderRadius: 8,
          border: "1px solid rgba(34,230,163,0.45)", background: "rgba(34,230,163,0.08)", marginBottom: 14,
        }}
      >
        <Ambulance size={26} strokeWidth={2} color="var(--rq-green)" />
        <div>
          <div style={{ fontSize: 26, fontWeight: 800, color: "var(--rq-white)", lineHeight: 1.05 }}>
            {assigned} / {units.length}
          </div>
          <div style={{ fontSize: 12, color: "rgba(234,244,255,0.7)" }}>Ambulances Assigned</div>
        </div>
      </div>

      <div style={{ fontSize: 12, color: "rgba(234,244,255,0.7)", marginBottom: 3 }}>Recommended Hospital</div>
      <div style={{ fontWeight: 800, fontSize: 16, color: "var(--rq-white)" }}>City General Hospital</div>
      <div style={{ display: "flex", gap: 6, marginTop: 8, flexWrap: "wrap" }}>
        {hospitalTags.map((tag) => <span key={tag} style={tagStyle}>{tag} ✓</span>)}
      </div>

      <DetailDrawer open={open} onClose={() => setOpen(false)} title="Medical & Hospital" icon={Hospital}>
        <div style={{ ...muted, marginBottom: 8 }}>Medical units ({units.length})</div>
        {units.map((u) => {
          const active = u.status !== "Standby";
          const c = active ? "var(--rq-cyan)" : "var(--rq-green)";
          return (
            <DrawerRow key={u.unit_id}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <Ambulance size={16} color={c} />
                  <div>
                    <div style={{ fontWeight: 700, color: "var(--rq-white)" }}>{u.unit_name}</div>
                    <div style={muted}>{u.personnel_count} personnel</div>
                  </div>
                </div>
                <span style={{ color: c, fontWeight: 800 }}>{u.status}</span>
              </div>
            </DrawerRow>
          );
        })}

        <div style={{ ...muted, margin: "16px 0 8px" }}>Recommended hospital</div>
        <DrawerRow accent="rgba(32,200,255,0.45)">
          <div style={{ fontWeight: 800, fontSize: 16, color: "var(--rq-white)" }}>City General Hospital</div>
          <div style={{ ...muted, marginTop: 4 }}>2.4 km · ETA ~6 min</div>
          <div style={{ display: "flex", gap: 6, marginTop: 8, flexWrap: "wrap" }}>
            {hospitalTags.map((tag) => <span key={tag} style={tagStyle}>{tag} ✓</span>)}
          </div>
        </DrawerRow>
      </DetailDrawer>
    </div>
  );
}

import React from "react";
import { Building2, Layers, User, Flame, Check } from "lucide-react";
import { useMapLayers, toggleMapLayer } from "../mapLayers.js";

const BLUE = "#2f8cff";
const RED = "#ff3b30";

// Map layer rows: first two use icons, the rest use checkbox-style icons (as in the reference)
const LAYER_DEFS = [
  { key: "occupants", label: "Occupants", kind: "icon", icon: User, color: "#3b9cff" },
  { key: "fire", label: "Fire / Smoke", kind: "icon", icon: Flame, color: "#ff7a29" },
  { key: "heatmap", label: "Risk Heatmap", kind: "check", color: BLUE },
  { key: "routes", label: "Rescue Routes", kind: "check", color: BLUE },
  { key: "blocked", label: "Blocked Routes", kind: "check", color: RED },
];

const panelTitle = { fontSize: 16, fontWeight: 800, color: "#fff", marginBottom: 12, letterSpacing: "0.01em" };

function CheckBox({ checked, color }) {
  return (
    <span
      style={{
        width: 18, height: 18, borderRadius: 4, flexShrink: 0,
        display: "inline-flex", alignItems: "center", justifyContent: "center",
        border: checked ? `1.5px solid ${color}` : "1.5px solid rgba(160,180,210,0.45)",
        background: checked ? color : "transparent",
        boxShadow: checked ? `0 0 8px ${color}66` : "none",
      }}
    >
      {checked && <Check size={13} strokeWidth={3.2} color="#fff" />}
    </span>
  );
}

function Switch({ on }) {
  return (
    <span
      style={{
        width: 38, height: 20, borderRadius: 999, position: "relative", flexShrink: 0,
        background: on ? "linear-gradient(90deg, #2563eb, #2f8cff)" : "rgba(90,110,140,0.35)",
        boxShadow: on ? "0 0 10px rgba(47,140,255,0.55)" : "none",
        transition: "background 0.15s ease",
      }}
    >
      <span
        style={{
          position: "absolute", top: 2, left: on ? 20 : 2, width: 16, height: 16, borderRadius: "50%",
          background: on ? "#fff" : "#9fb0c8", transition: "left 0.15s ease",
        }}
      />
    </span>
  );
}

function LayerRow({ def, on, onToggle }) {
  const Icon = def.icon;
  return (
    <button
      onClick={onToggle}
      style={{
        display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10,
        width: "100%", background: "transparent", border: "none", cursor: "pointer",
        padding: "7px 2px", color: "var(--rq-white)", fontSize: 14, fontWeight: 500,
      }}
    >
      <span style={{ display: "flex", alignItems: "center", gap: 10 }}>
        {def.kind === "icon" ? (
          <Icon size={18} strokeWidth={2.2} color={def.color} fill={def.key === "fire" ? def.color : "none"} fillOpacity={0.25} />
        ) : (
          <CheckBox checked={on} color={def.color} />
        )}
        {def.label}
      </span>
      <Switch on={on} />
    </button>
  );
}

function FloorRow({ active, onClick, icon: Icon, label, badge }) {
  return (
    <button
      onClick={onClick}
      style={{
        display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10,
        width: "100%", textAlign: "left", cursor: "pointer",
        padding: "9px 12px", borderRadius: 8,
        background: active
          ? "linear-gradient(90deg, rgba(37,99,235,0.55), rgba(37,99,235,0.28))"
          : "rgba(255,255,255,0.03)",
        border: active ? "1px solid rgba(80,160,255,0.75)" : "1px solid rgba(34,211,238,0.12)",
        boxShadow: active ? "0 0 12px rgba(47,140,255,0.35)" : "none",
        color: "#fff", fontSize: 14, fontWeight: active ? 700 : 600,
      }}
    >
      <span style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <Icon size={18} strokeWidth={2.2} color={active ? "#fff" : "var(--rq-white)"} />
        {label}
      </span>
      {badge && (
        <span
          style={{
            minWidth: 22, height: 22, borderRadius: "50%", padding: "0 5px",
            display: "inline-flex", alignItems: "center", justifyContent: "center",
            fontSize: 12, fontWeight: 800, color: "#fff",
            background: badge.critical ? RED : "rgba(120,140,170,0.35)",
            boxShadow: badge.critical ? "0 0 10px rgba(255,59,48,0.6)" : "none",
          }}
        >
          {badge.count}
        </span>
      )}
    </button>
  );
}

export default function FloorSidebar({ floors, selectedFloor, onSelectFloor, rooms }) {
  // shared with the 3D building, so these switches really control what the map shows
  const layers = useMapLayers();
  const toggleLayer = toggleMapLayer;

  const alertCount = (n) =>
    rooms.filter((r) => r.floor_number === n && (r.risk_level === "Critical" || r.risk_level === "High Risk")).length;
  const hasCritical = (n) => rooms.some((r) => r.floor_number === n && r.risk_level === "Critical");

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <div className="glass-panel rq-tech" style={{ padding: 14 }}>
        <div style={panelTitle}>Building Floors</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <FloorRow
            active={selectedFloor === null}
            onClick={() => onSelectFloor(null)}
            icon={Building2}
            label="All Floors"
          />
          {floors
            .slice()
            .sort((a, b) => b.floor_number - a.floor_number)
            .map((f) => (
              <FloorRow
                key={f.floor_number}
                active={selectedFloor === f.floor_number}
                onClick={() => onSelectFloor(f.floor_number)}
                icon={Layers}
                label={f.floor_label}
                badge={{ count: alertCount(f.floor_number), critical: hasCritical(f.floor_number) }}
              />
            ))}
        </div>
      </div>

      <div className="glass-panel rq-tech" style={{ padding: 14 }}>
        <div style={panelTitle}>Map Layers</div>
        {LAYER_DEFS.map((def) => (
          <LayerRow key={def.key} def={def} on={layers[def.key]} onToggle={() => toggleLayer(def.key)} />
        ))}
      </div>
    </div>
  );
}

import React, { useState } from "react";
import { PieChart, Pie, Cell } from "recharts";
import { Users2 } from "lucide-react";
import { PanelHeader, DetailDrawer, DrawerRow, muted } from "./PanelKit.jsx";

const COLORS = { Critical: "#ff3b30", "High Risk": "#ffb020", Safe: "#22e6a3", Animal: "#3b9cff" };
const ORDER = ["Critical", "High Risk", "Safe", "Animal"];

// Animals get their own slice if the backend marks them (occupant_type / type / category)
const isAnimal = (o) => /animal|dog|cat|pet/i.test(String(o.occupant_type || o.type || o.category || ""));
const groupOf = (o) => (isAnimal(o) ? "Animal" : o.risk_status);
const roomOf = (o) => o.room_id || o.current_room || o.location || "—";

// Sensors only know how many people/animals are in a room and how at-risk it is — not who
// they are — so the drawer groups by room instead of listing individual names.
function groupByRoom(occupants) {
  const byRoom = {};
  occupants.forEach((o) => {
    const room = roomOf(o);
    if (!byRoom[room]) byRoom[room] = { room, people: 0, animals: 0, worst: "Safe" };
    const entry = byRoom[room];
    if (isAnimal(o)) entry.animals += 1;
    else entry.people += 1;
    if ((RISK_RANK[o.risk_status] ?? 9) < (RISK_RANK[entry.worst] ?? 9)) entry.worst = o.risk_status;
  });
  return Object.values(byRoom).sort((a, b) => a.room.localeCompare(b.room));
}
const RISK_RANK = { Critical: 0, "High Risk": 1, Safe: 2 };

export default function OccupantChart({ occupants }) {
  const [open, setOpen] = useState(false);

  const counts = { Critical: 0, "High Risk": 0, Safe: 0, Animal: 0 };
  occupants.forEach((o) => {
    const g = groupOf(o);
    if (counts[g] !== undefined) counts[g] += 1;
  });
  const total = occupants.length;
  const data = ORDER.map((name) => ({ name, value: counts[name] })).filter((d) => d.value > 0);
  const legend = ORDER.filter((n) => n !== "Animal" || counts.Animal > 0);

  return (
    <div className="glass-panel rq-tech" style={{ padding: 16 }}>
      <PanelHeader icon={Users2} title="Occupant Intelligence" onAction={() => setOpen(true)} />

      <div style={{ display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap" }}>
        <div style={{ position: "relative", width: 140, height: 140, flexShrink: 0 }}>
          <PieChart width={140} height={140}>
            <Pie
              data={data.length ? data : [{ name: "none", value: 1 }]}
              dataKey="value" nameKey="name" innerRadius={48} outerRadius={66}
              paddingAngle={data.length > 1 ? 3 : 0} stroke="none" startAngle={90} endAngle={-270}
            >
              {(data.length ? data : [{ name: "none" }]).map((d) => (
                <Cell key={d.name} fill={COLORS[d.name] || "#1b2b45"} />
              ))}
            </Pie>
          </PieChart>
          <div
            style={{
              position: "absolute", inset: 0, display: "flex", flexDirection: "column",
              alignItems: "center", justifyContent: "center", pointerEvents: "none",
            }}
          >
            <div style={{ fontSize: 30, fontWeight: 800, color: "var(--rq-white)", lineHeight: 1 }}>{total}</div>
            <div style={{ fontSize: 10.5, color: "rgba(234,244,255,0.65)", marginTop: 3 }}>Total Occupants</div>
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 9, flex: 1, minWidth: 110 }}>
          {legend.map((name) => (
            <div key={name} style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ width: 9, height: 9, borderRadius: "50%", background: COLORS[name], flexShrink: 0 }} />
              <span style={{ fontSize: 17, fontWeight: 800, color: "var(--rq-white)", minWidth: 18 }}>{counts[name]}</span>
              <span style={{ fontSize: 13, fontWeight: 600, color: COLORS[name] }}>{name}</span>
            </div>
          ))}
        </div>
      </div>

      <DetailDrawer open={open} onClose={() => setOpen(false)} title="Occupant Intelligence" icon={Users2}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 8, marginBottom: 16 }}>
          {legend.map((name) => (
            <DrawerRow key={name} accent={COLORS[name]}>
              <div style={{ fontSize: 24, fontWeight: 800, color: COLORS[name] }}>{counts[name]}</div>
              <div style={muted}>{name}</div>
            </DrawerRow>
          ))}
        </div>
        <div style={{ ...muted, marginBottom: 8 }}>By room ({groupByRoom(occupants).length} rooms)</div>
        {groupByRoom(occupants).map((r) => (
          <DrawerRow key={r.room} accent={COLORS[r.worst]}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
              <div style={{ fontWeight: 700, color: "var(--rq-white)" }}>Room {r.room}</div>
              <span style={{ color: COLORS[r.worst], fontWeight: 700, fontSize: 12 }}>{r.worst}</span>
            </div>
            <div style={{ ...muted, marginTop: 4 }}>
              {r.people} {r.people === 1 ? "person" : "people"}
              {r.animals > 0 && ` · ${r.animals} animal${r.animals === 1 ? "" : "s"}`}
            </div>
          </DrawerRow>
        ))}
        {total === 0 && <div style={muted}>No occupants detected.</div>}
      </DetailDrawer>
    </div>
  );
}

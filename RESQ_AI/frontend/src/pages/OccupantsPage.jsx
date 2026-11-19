import React, { useEffect, useState } from "react";
import { Loading, ErrorState } from "../components/Common.jsx";
import { getOccupants, getRooms } from "../api/client.js";
import { PawPrint, Users, AlertTriangle, Flame, ShieldCheck } from "lucide-react";

function Stat({ icon: Icon, label, value, color, sub }) {
  return (
    <div className="glass-panel" style={{ padding: 18, display: "flex", alignItems: "center", gap: 14, borderColor: color }}>
      <div style={{ width: 46, height: 46, borderRadius: 12, display: "grid", placeItems: "center", background: `${color}22`, color }}>
        <Icon size={24} />
      </div>
      <div>
        <div style={{ fontSize: 30, fontWeight: 800, lineHeight: 1, color }}>{value}</div>
        <div style={{ fontSize: 12.5, marginTop: 4 }}>{label}</div>
        {sub && <div style={{ fontSize: 11, color: "var(--text-muted)" }}>{sub}</div>}
      </div>
    </div>
  );
}

export default function OccupantsPage() {
  const [occupants, setOccupants] = useState([]);
  const [rooms, setRooms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const load = async () => {
    try {
      const [o, r] = await Promise.all([getOccupants(), getRooms()]);
      setOccupants(o);
      setRooms(r);
      setError(false);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  if (loading) return <Loading />;
  if (error) return <ErrorState onRetry={load} />;

  const isAnimal = (o) => o.type !== "Human";
  const trapped = occupants.filter((o) => o.is_trapped);
  const trappedPeople = trapped.filter((o) => !isAnimal(o)).length;
  const trappedAnimals = trapped.filter(isAnimal).length;
  const totalPeople = occupants.filter((o) => !isAnimal(o)).length;
  const totalAnimals = occupants.filter(isAnimal).length;
  const count = (lvl) => occupants.filter((o) => o.risk_status === lvl).length;

  // per-floor counts (no names)
  const floorOf = Object.fromEntries(rooms.map((r) => [r.room_id, r.floor_number]));
  const floors = {};
  occupants.forEach((o) => {
    const f = floorOf[o.room_id] ?? "-";
    floors[f] = floors[f] || { people: 0, animals: 0, trapped: 0 };
    if (isAnimal(o)) floors[f].animals += 1; else floors[f].people += 1;
    if (o.is_trapped) floors[f].trapped += 1;
  });
  const floorRows = Object.entries(floors).sort((a, b) => Number(a[0]) - Number(b[0]));

  return (
    <div className="fade-in" style={{ display: "grid", gap: 16 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14 }}>
        <Stat icon={AlertTriangle} label="Total Trapped" value={trapped.length} color="#ff3b30" sub="people + living things" />
        <Stat icon={Users} label="People Trapped" value={trappedPeople} color="#ffb020" />
        <Stat icon={PawPrint} label="Animals Trapped" value={trappedAnimals} color="#20c8ff" />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 14 }}>
        <Stat icon={Users} label="People in Building" value={totalPeople} color="#eaf4ff" />
        <Stat icon={PawPrint} label="Animals in Building" value={totalAnimals} color="#eaf4ff" />
        <Stat icon={Flame} label="Critical" value={count("Critical")} color="#ff3b30" />
        <Stat icon={AlertTriangle} label="High Risk" value={count("High Risk")} color="#ffb020" />
        <Stat icon={ShieldCheck} label="Safe" value={count("Safe")} color="#22e6a3" />
      </div>

      <div className="glass-panel" style={{ padding: 18 }}>
        <h3 style={{ margin: "0 0 12px", fontSize: 15 }}>Floor-wise Count</h3>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ textAlign: "left", color: "var(--text-muted)", borderBottom: "1px solid var(--border-subtle)" }}>
              <th style={{ padding: "8px 6px" }}>Floor</th>
              <th style={{ padding: "8px 6px" }}>People</th>
              <th style={{ padding: "8px 6px" }}>Animals</th>
              <th style={{ padding: "8px 6px" }}>Trapped</th>
            </tr>
          </thead>
          <tbody>
            {floorRows.map(([f, v]) => (
              <tr key={f} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                <td style={{ padding: "8px 6px" }}>Floor {f}</td>
                <td style={{ padding: "8px 6px" }}>{v.people}</td>
                <td style={{ padding: "8px 6px" }}>{v.animals}</td>
                <td style={{ padding: "8px 6px", color: v.trapped ? "#ff3b30" : undefined, fontWeight: v.trapped ? 700 : 400 }}>{v.trapped}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

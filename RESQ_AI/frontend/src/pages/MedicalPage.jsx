import React, { useEffect, useState } from "react";
import { Loading, ErrorState } from "../components/Common.jsx";
import { getMedicalSupport } from "../api/client.js";
import { Stethoscope } from "lucide-react";

const STATUS_COLOR = { "En Route": "var(--orange)", "On Scene": "var(--red)", Standby: "var(--green)" };

export default function MedicalPage() {
  const [units, setUnits] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const load = async () => {
    try {
      setUnits(await getMedicalSupport());
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

  return (
    <div className="fade-in" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 16 }}>
      {units.map((u) => (
        <div key={u.unit_id} className="glass-panel" style={{ padding: 18 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, fontWeight: 800 }}>
              <Stethoscope size={16} color="var(--cyan)" /> {u.unit_name}
            </div>
            <span style={{ color: STATUS_COLOR[u.status], fontWeight: 700, fontSize: 11.5 }}>{u.status}</span>
          </div>
          <div style={{ fontSize: 12.5, color: "var(--text-muted)", marginTop: 10 }}>
            Personnel: {u.personnel_count}<br />
            Assigned Room: {u.assigned_room || "—"}<br />
            ETA: {u.eta_minutes} min
          </div>
        </div>
      ))}
    </div>
  );
}

import React, { useEffect, useState } from "react";
import { Loading, ErrorState } from "../components/Common.jsx";
import { getIncidents, getRooms, getOccupants, getAuditLogs } from "../api/client.js";
import { useAuth, can } from "../components/AuthContext.jsx";
import { Download, FileBarChart } from "lucide-react";

export default function ReportsPage() {
  const { role } = useAuth();
  const isAdmin = can(role, "admin");
  const [audit, setAudit] = useState([]);
  const [incidents, setIncidents] = useState([]);
  const [rooms, setRooms] = useState([]);
  const [occupants, setOccupants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const load = async () => {
    try {
      const [i, r, o] = await Promise.all([getIncidents(), getRooms(), getOccupants()]);
      setIncidents(i);
      setRooms(r);
      setOccupants(o);
      if (isAdmin) setAudit(await getAuditLogs(50).catch(() => []));
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

  const totalIncidents = incidents.length;
  const criticalIncidents = incidents.filter((i) => i.severity === "Critical").length;
  // Actual tracked metric: minutes from incident detection until the rescue team is on scene
  const responded = incidents.filter((i) => i.on_scene_at && i.detected_at);
  const avgResponse = responded.length
    ? (responded.reduce((sum, i) => sum + (new Date(i.on_scene_at) - new Date(i.detected_at)), 0) / responded.length / 60000).toFixed(1)
    : "—";
  const peopleRescued = occupants.filter((o) => o.is_rescued && o.type === "Human").length;
  const roomsAffected = new Set(incidents.map((i) => i.room_id)).size;
  const floorRiskCount = {};
  rooms.forEach((r) => {
    if (r.risk_level === "Critical" || r.risk_level === "High Risk") {
      floorRiskCount[r.floor_number] = (floorRiskCount[r.floor_number] || 0) + 1;
    }
  });
  const highestRiskFloor = Object.entries(floorRiskCount).sort((a, b) => b[1] - a[1])[0]?.[0] ?? "—";

  // RFC 4180: wrap in quotes when a value has a comma, quote or newline; double any quotes.
  // A leading = + - @ is prefixed with ' so spreadsheets do not run it as a formula.
  const csvCell = (v) => {
    let s = v === null || v === undefined ? "" : String(v);
    if (/^[=+\-@]/.test(s) && Number.isNaN(Number(s))) s = `'${s}`;
    return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };

  const generateReport = () => {
    const rows = [
      ["Metric", "Value"],
      ["Total Incidents", totalIncidents],
      ["Critical Incidents", criticalIncidents],
      ["Average Response Time (min)", avgResponse],
      ["People Rescued", peopleRescued],
      ["Rooms Affected", roomsAffected],
      ["Highest Risk Floor", highestRiskFloor],
      [],
      ["Incident ID", "Room", "Floor", "Type", "Severity", "Stage", "Risk Score", "Detected At", "On Scene At", "Resolved At"],
      ...incidents.map((i) => [i.incident_id, i.room_id, i.floor, i.incident_type, i.severity, i.lifecycle, i.risk_score, i.detected_at, i.on_scene_at, i.resolved_at]),
    ];
    const csv = "\uFEFF" + rows.map((r) => r.map(csvCell).join(",")).join("\r\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `resq-ai-incident-report-${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const stats = [
    ["Total Incidents", totalIncidents],
    ["Critical Incidents", criticalIncidents],
    ["Avg Response Time", avgResponse === "—" ? "— (no arrival yet)" : `${avgResponse} min`],
    ["People Rescued", peopleRescued],
    ["Rooms Affected", roomsAffected],
    ["Highest Risk Floor", highestRiskFloor],
  ];

  return (
    <div className="fade-in glass-panel" style={{ padding: 20 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 18 }}>
        <h3 style={{ margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
          <FileBarChart size={18} color="var(--cyan)" /> Incident Reports
        </h3>
        <button className="btn" onClick={generateReport}>
          <Download size={13} style={{ marginRight: 5, verticalAlign: -2 }} />
          Generate Incident Report
        </button>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 14 }}>
        {stats.map(([label, value]) => (
          <div key={label} className="glass-panel" style={{ padding: 14 }}>
            <div style={{ fontSize: 22, fontWeight: 800, color: "#fff" }}>{value}</div>
            <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4, textTransform: "uppercase" }}>{label}</div>
          </div>
        ))}
      </div>
      <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 10 }}>
        Avg Response Time = detection until the rescue team is on scene (only incidents where a team has arrived).
      </div>

      {isAdmin && (
        <div style={{ marginTop: 22 }}>
          <h3 style={{ margin: "0 0 10px", fontSize: 14 }}>Audit Log (last {audit.length})</h3>
          <div style={{ overflowX: "auto", maxHeight: 320, overflowY: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
              <thead>
                <tr style={{ textAlign: "left", color: "var(--text-muted)", borderBottom: "1px solid var(--border-subtle)" }}>
                  {["Time", "User", "Action", "Target", "Details", "Result"].map((h) => <th key={h} style={{ padding: "6px 6px" }}>{h}</th>)}
                </tr>
              </thead>
              <tbody>
                {audit.map((a) => (
                  <tr key={a.id} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                    <td style={{ padding: "6px 6px", whiteSpace: "nowrap" }}>{new Date(a.timestamp).toLocaleTimeString()}</td>
                    <td style={{ padding: "6px 6px" }}>{a.username || "—"} <span style={{ color: "var(--text-muted)" }}>({a.role || "-"})</span></td>
                    <td style={{ padding: "6px 6px" }}>{a.action}</td>
                    <td style={{ padding: "6px 6px" }}>{a.target || ""}</td>
                    <td style={{ padding: "6px 6px", color: "var(--text-muted)" }}>{a.detail || ""}</td>
                    <td style={{ padding: "6px 6px", color: a.success ? "var(--green)" : "var(--red)" }}>{a.success ? "OK" : "Failed"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

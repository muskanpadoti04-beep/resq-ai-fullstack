import React, { useEffect, useState } from "react";
import { Loading, ErrorState } from "../components/Common.jsx";
import { getRescueTeams, dispatchTeam, arriveTeam, completeRescue, errorMessage } from "../api/client.js";
import { Truck } from "lucide-react";
import { useAuth, can } from "../components/AuthContext.jsx";

const STATUS_COLOR = { "En Route": "var(--orange)", "On Scene": "var(--red)", Standby: "var(--green)" };

export default function RescueTeamsPage({ showToast }) {
  const { role } = useAuth();
  const canOperate = can(role, "operator");
  const [teams, setTeams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const load = async () => {
    try {
      setTeams(await getRescueTeams());
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

  const handleDispatch = async (teamId) => {
    try {
      await dispatchTeam(teamId);
      showToast("success", "Team dispatched.");
      load();
    } catch (e) {
      showToast("error", errorMessage(e, "Dispatch failed."));
    }
  };

  const handleArrive = async (teamId) => {
    try {
      await arriveTeam(teamId);
      showToast("success", "Team marked as arrived on scene.");
      load();
    } catch (e) {
      showToast("error", errorMessage(e, "Could not mark the team as arrived."));
    }
  };

  const handleComplete = async (teamId) => {
    try {
      const r = await completeRescue(teamId);
      showToast("success", `Rescue complete in ${r.room_id}: ${r.people_rescued} people, ${r.animals_rescued} animals rescued.`);
      load();
    } catch (e) {
      showToast("error", errorMessage(e, "Could not complete rescue."));
    }
  };

  return (
    <div className="fade-in" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 16 }}>
      {teams.map((t) => (
        <div key={t.team_id} className="glass-panel" style={{ padding: 18 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, fontWeight: 800 }}>
              <Truck size={16} color="var(--cyan)" /> {t.team_name}
            </div>
            <span style={{ color: STATUS_COLOR[t.status], fontWeight: 700, fontSize: 11.5 }}>{t.status}</span>
          </div>
          <div style={{ fontSize: 12.5, color: "var(--text-muted)", marginTop: 10 }}>
            Location: {t.current_location}<br />
            Assigned Room: {t.assigned_room || "—"}<br />
            ETA: {t.eta_minutes} min
          </div>
          <button
            className="btn"
            style={{ marginTop: 12, width: "100%" }}
            disabled={t.status !== "Standby" || !canOperate}
            title={canOperate ? "Sends the team to the highest-risk incident without a team" : "Operator access required"}
            onClick={() => handleDispatch(t.team_id)}
          >
            {t.status === "Standby" ? "Dispatch" : "Already Deployed"}
          </button>
          {t.status === "En Route" && (
            <button className="btn" disabled={!canOperate} style={{ marginTop: 8, width: "100%" }} onClick={() => handleArrive(t.team_id)}>
              Mark Arrived
            </button>
          )}
          {t.status === "On Scene" && (
            <button
              className="btn"
              disabled={!canOperate}
              style={{ marginTop: 8, width: "100%", borderColor: "rgba(34,230,163,0.6)", color: "#22e6a3" }}
              onClick={() => handleComplete(t.team_id)}
            >
              Mark Rescue Complete
            </button>
          )}
        </div>
      ))}
    </div>
  );
}

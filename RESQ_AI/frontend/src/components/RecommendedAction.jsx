import React, { useEffect, useState } from "react";
import { SectionTitle } from "./Common.jsx";
import { Navigation, Route, TriangleAlert, Truck, CheckCircle2 } from "lucide-react";
import {
  navigateTeam, dispatchTeam, arriveTeam, completeRescue, getRescueRoute, errorMessage,
} from "../api/client.js";
import { useAuth, can } from "./AuthContext.jsx";

// "Stair B (Floor 1)" ... "Stair B (Floor 4)" -> one step "Stair B F1→F4"
function summarize(path) {
  const out = [];
  let i = 0;
  while (i < path.length) {
    const n = path[i];
    if (n.type === "stair") {
      let j = i;
      while (j + 1 < path.length && path[j + 1].type === "stair") j += 1;
      const stair = n.label.replace(/\s*\(.*\)/, "");
      out.push(j > i ? `${stair} F${n.floor}→F${path[j].floor}` : stair);
      i = j + 1;
    } else {
      out.push(n.type === "room" ? n.label.replace("Room ", "") : n.label);
      i += 1;
    }
  }
  return out;
}

export default function RecommendedAction({ team, incident, teams = [], showToast, onNavigated }) {
  const { role } = useAuth();
  const canOperate = can(role, "operator");
  const [busy, setBusy] = useState(false);
  const [route, setRoute] = useState(null);

  const roomId = incident?.room_id;
  useEffect(() => {
    let cancelled = false;
    if (!roomId) { setRoute(null); return undefined; }
    getRescueRoute(roomId)
      .then((r) => { if (!cancelled) setRoute(r); })
      .catch(() => { if (!cancelled) setRoute(null); });
    return () => { cancelled = true; };
  }, [roomId, incident?.lifecycle, incident?.risk_score]);

  const run = async (fn, okMessage, failMessage) => {
    setBusy(true);
    try {
      const res = await fn();
      showToast("success", typeof okMessage === "function" ? okMessage(res) : okMessage);
      onNavigated && onNavigated(res);
    } catch (e) {
      showToast("error", errorMessage(e, failMessage));
    } finally {
      setBusy(false);
    }
  };

  if (!incident) {
    return (
      <div className="glass-panel" style={{ padding: 18 }}>
        <SectionTitle>Recommended Action</SectionTitle>
        <p style={{ color: "var(--text-muted)", fontSize: 13 }}>Select an incident to see the recommended action.</p>
      </div>
    );
  }

  const resolved = incident.lifecycle === "Resolved";
  const standby = teams.find((t) => t.status === "Standby");

  return (
    <div className="glass-panel fade-in" style={{ padding: 18 }}>
      <SectionTitle>Recommended Action</SectionTitle>

      {resolved ? (
        <p style={{ color: "var(--text-muted)", fontSize: 13, display: "flex", alignItems: "center", gap: 6 }}>
          <CheckCircle2 size={15} color="var(--rq-green)" /> Incident resolved. No action needed.
        </p>
      ) : (
        <>
          {team ? (
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <div style={{ fontWeight: 800, fontSize: 14 }}>{team.team_name}</div>
                <div style={{ fontSize: 12, color: "var(--text-muted)" }}>{team.status}</div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div style={{ fontSize: 18, fontWeight: 800, color: "var(--cyan)" }}>
                  {team.status === "On Scene" ? "On scene" : `~${team.eta_minutes} min`}
                </div>
                <div style={{ fontSize: 10.5, color: "var(--text-muted)" }}>{team.status === "On Scene" ? "" : "ETA"}</div>
              </div>
            </div>
          ) : (
            <div style={{ fontSize: 13, color: "var(--text-muted)" }}>
              No rescue team assigned yet.{" "}
              {standby ? <>Suggested: <b style={{ color: "#fff" }}>{standby.team_name}</b></> : "No team is on standby."}
            </div>
          )}

          {route && route.found && (
            <div style={{ marginTop: 14, fontSize: 12, color: "var(--text-muted)" }}>
              <div style={{ display: "flex", alignItems: "flex-start", gap: 6 }}>
                <Route size={14} color="var(--cyan)" style={{ marginTop: 2, flexShrink: 0 }} />
                <span>{summarize(route.path).join(" → ")}</span>
              </div>
              <div style={{ marginTop: 4, paddingLeft: 20 }}>
                {route.distance_m} m · about {route.estimated_seconds} s
              </div>
              {route.blocked_exits?.length > 0 && (
                <div style={{ marginTop: 4, paddingLeft: 20, color: "var(--rq-amber)" }}>
                  Blocked exit avoided: {route.blocked_exits.join(", ")}
                </div>
              )}
              {route.through_hazard && (
                <div style={{ marginTop: 4, paddingLeft: 20, color: "var(--rq-amber)", display: "flex", gap: 4, alignItems: "flex-start" }}>
                  <TriangleAlert size={13} style={{ marginTop: 1, flexShrink: 0 }} />
                  <span>Passes a hazard: {[...new Set(route.warnings)].join("; ")}</span>
                </div>
              )}
            </div>
          )}
          {route && !route.found && (
            <div style={{ marginTop: 14, fontSize: 12, color: "var(--rq-red)" }}>
              No safe route found to {incident.room_id}. Every path is blocked.
            </div>
          )}

          <div style={{ display: "grid", gap: 8, marginTop: 14 }}>
            {!team && (
              <button className="btn" disabled={!canOperate || busy || !standby}
                      title={canOperate ? "" : "Operator access required"}
                      style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 6 }}
                      onClick={() => run(() => dispatchTeam(standby.team_id, incident.incident_id),
                        (r) => `${r.team_name} dispatched to ${incident.room_id}`, "Could not dispatch the team.")}>
                <Truck size={14} /> {standby ? `Dispatch ${standby.team_name}` : "No team available"}
              </button>
            )}
            {team && team.status === "En Route" && (
              <>
                <button className="btn" disabled={!canOperate || busy}
                        style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 6 }}
                        onClick={() => run(() => navigateTeam(team.team_id),
                          `Navigation started for ${team.team_name}`, "Failed to start navigation.")}>
                  <Navigation size={14} /> Start Navigation
                </button>
                <button className="btn" disabled={!canOperate || busy}
                        onClick={() => run(() => arriveTeam(team.team_id),
                          `${team.team_name} arrived on scene`, "Could not mark the team as arrived.")}>
                  Mark Arrived
                </button>
              </>
            )}
            {team && team.status === "On Scene" && (
              <button className="btn" disabled={!canOperate || busy}
                      style={{ borderColor: "rgba(34,230,163,0.6)", color: "#22e6a3" }}
                      onClick={() => run(() => completeRescue(team.team_id),
                        (r) => `Rescue complete: ${r.people_rescued} people, ${r.animals_rescued} animals`, "Could not complete the rescue.")}>
                Mark Rescue Complete
              </button>
            )}
          </div>
        </>
      )}
    </div>
  );
}

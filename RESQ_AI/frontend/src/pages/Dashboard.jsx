import AlertBanner from "../components/AlertBanner.jsx";
import LifecycleStepper from "../components/LifecycleStepper.jsx";
import LiveTrend from "../components/LiveTrend.jsx";
import { useAuth, can } from "../components/AuthContext.jsx";
import React, { useEffect, useState, useCallback, useRef } from "react";
import StatusCards from "../components/StatusCards.jsx";
import CardDetailModal from "../components/CardDetailModal.jsx";
import FloorSidebar from "../components/FloorSidebar.jsx";
import BuildingMap from "../components/BuildingMap.jsx";
import ActiveIncidentPanel from "../components/ActiveIncidentPanel.jsx";
import RecommendedAction from "../components/RecommendedAction.jsx";
import ForecastPanel from "../components/ForecastPanel.jsx";
import OccupantChart from "../components/OccupantChart.jsx";
import { RescueTeamsPanel, MedicalPanel } from "../components/ResponsePanels.jsx";
import { IncidentTimeline } from "../components/FeedsAndTimeline.jsx";
import { Loading, ErrorState } from "../components/Common.jsx";
import {
  getDashboardSummary, getFloors, getRooms, getOccupants, getActiveIncidents,
  getRescueTeams, getMedicalSupport, getTimeline, acknowledgeIncident, resolveIncident, getRescueRoute, simulateFire, resetDemo, errorMessage, lastApiError,
} from "../api/client.js";

export default function Dashboard({ showToast }) {
  const { role } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(true);
  const [selectedFloor, setSelectedFloor] = useState(null);
  const [selectedRoomId, setSelectedRoomId] = useState(null);
  const [simulating, setSimulating] = useState(false);
  const [openCard, setOpenCard] = useState(null); // which status card popup is open
  const [routePath, setRoutePath] = useState(null); // backend-computed rescue route for the selected incident

  const routeRoom = data ? (data.incidents.find((i) => i.room_id === selectedRoomId) || data.incidents[0])?.room_id : null;
  const routeKey = data
    ? data.incidents.map((i) => `${i.incident_id}:${i.lifecycle}`).join(",") + "|" + data.rooms.filter((r) => r.fire_status === "active").length
    : "";
  useEffect(() => {
    let off = false;
    if (!routeRoom) { setRoutePath(null); return undefined; }
    getRescueRoute(routeRoom)
      .then((r) => { if (!off) setRoutePath(r.found ? r.path : null); })
      .catch(() => { if (!off) setRoutePath(null); });
    return () => { off = true; };
  }, [routeRoom, routeKey]);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);

  const loadAll = useCallback(async () => {
    try {
      const [summary, floors, rooms, occupants, incidents, teams, medical, timeline] = await Promise.all([
        getDashboardSummary(), getFloors(), getRooms(), getOccupants(), getActiveIncidents(),
        getRescueTeams(), getMedicalSupport(), getTimeline(),
      ]);
      setData({ summary, floors, rooms, occupants, incidents, teams, medical, timeline });
      setError(false);
      setLastUpdated(new Date());
      if (!selectedRoomId && incidents.length > 0) {
        setSelectedRoomId(incidents[0].room_id);
      }
      return true;
    } catch (e) {
      setError(true);
      return false;
    } finally {
      setLoading(false);
    }
  }, [selectedRoomId]);

  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Refresh / Simulate Fire buttons now live in the Navbar; they trigger this page through window events
  const actionsRef = useRef({});
  const handleRefresh = async () => {
    if (refreshing) return;
    setRefreshing(true);
    const started = Date.now();
    const ok = await loadAll();
    // keep the spinner visible for at least a moment so the click is noticeable
    const wait = Math.max(0, 600 - (Date.now() - started));
    await new Promise((r) => setTimeout(r, wait));
    setRefreshing(false);
    showToast(ok ? "success" : "error", ok ? "Dashboard refreshed with latest data." : `Refresh failed. ${lastApiError.message || "Backend unreachable."}`);
  };
  actionsRef.current.refresh = handleRefresh;
  useEffect(() => {
    const onRefresh = () => actionsRef.current.refresh && actionsRef.current.refresh();
    const onSimulate = () => actionsRef.current.simulate && actionsRef.current.simulate();
    window.addEventListener("resq:refresh", onRefresh);
    window.addEventListener("resq:simulate", onSimulate);
    return () => {
      window.removeEventListener("resq:refresh", onRefresh);
      window.removeEventListener("resq:simulate", onSimulate);
      window.dispatchEvent(new CustomEvent("resq:simulating", { detail: false }));
      window.dispatchEvent(new CustomEvent("resq:refreshing", { detail: false }));
    };
  }, []);
  useEffect(() => {
    window.dispatchEvent(new CustomEvent("resq:simulating", { detail: simulating }));
  }, [simulating]);
  useEffect(() => {
    window.dispatchEvent(new CustomEvent("resq:refreshing", { detail: refreshing }));
  }, [refreshing]);
  useEffect(() => {
    const id = setInterval(() => loadAll(), 4000);
    return () => clearInterval(id);
  }, [loadAll]);

  if (loading) return <Loading />;
  if (error || !data) return <ErrorState onRetry={handleRefresh} />;

  const filteredRooms = selectedFloor === null ? data.rooms : data.rooms.filter((r) => r.floor_number === selectedFloor);
  const selectedIncident = data.incidents.find((i) => i.room_id === selectedRoomId) || data.incidents[0] || null;
  const assignedTeam = selectedIncident
    ? data.teams.find((t) => t.team_id === selectedIncident.assigned_team_id)
      || data.teams.find((t) => t.assigned_room === selectedIncident.room_id)
    : null;

  const criticalOcc = data.occupants.filter((o) => !o.is_rescued && o.risk_status === "Critical").length;
  const highOcc = data.occupants.filter((o) => !o.is_rescued && o.risk_status === "High Risk").length;
  const enRoute = data.teams.filter((t) => t.status === "En Route").length;
  const onScene = data.teams.filter((t) => t.status === "On Scene").length;
  const breakdown = {
    active_incidents: data.incidents[0] ? `Room ${data.incidents[0].room_id}` : undefined,
    people_at_risk: `${criticalOcc} Critical · ${highOcc} High`,
    active_rescue_teams: `${enRoute} En Route · ${onScene} On Scene`,
    medical_support: `${data.medical.length} units on roster`,
  };

  const handleAcknowledge = async (incidentId) => {
    try {
      await acknowledgeIncident(incidentId);
      showToast("success", "Incident acknowledged.");
      loadAll();
    } catch (e) {
      showToast("error", errorMessage(e, "Could not acknowledge incident."));
    }
  };

  const handleResolve = async (incidentId) => {
    try {
      await resolveIncident(incidentId);
      showToast("success", "Incident resolved.");
      loadAll();
    } catch (e) {
      showToast("error", errorMessage(e, "Could not resolve the incident."));
    }
  };

  const handleSimulate = async () => {
    setSimulating(true);
    try {
      const res = await simulateFire();
      showToast("success", `Simulated fire event in ${res.room_id}`);
      await loadAll();
      setSelectedRoomId(res.room_id);
      window.dispatchEvent(new CustomEvent("resq:fire", { detail: res.room_id }));
    } catch (e) {
      showToast("error", errorMessage(e, "Simulation failed."));
    } finally {
      setSimulating(false);
    }
  };
  actionsRef.current.simulate = handleSimulate;

  const handleReset = async () => {
    if (!window.confirm("Reset demo? All simulated fires and rescues will be cleared.")) return;
    try {
      await resetDemo();
      setSelectedRoomId(null);
      setSelectedFloor(null);
      setOpenCard(null);
      await loadAll();
      showToast("success", "Demo reset. Original data restored.");
    } catch (e) {
      showToast("error", errorMessage(e, "Reset failed."));
    }
  };

  return (
    <div className="fade-in" style={{ display: "flex", flexDirection: "column", gap: 18 }}>
      <div style={{ fontSize: 11, color: "var(--text-muted)", textAlign: "right", marginBottom: -10 }}>
        {lastUpdated && <>Last updated {lastUpdated.toLocaleTimeString()} &nbsp;·&nbsp; </>}
        {can(role, "admin") && (
          <button
            onClick={handleReset}
            style={{ background: "none", border: "none", padding: 0, color: "var(--cyan)", cursor: "pointer", fontSize: 11, textDecoration: "underline" }}
          >
            Reset demo
          </button>
        )}
      </div>
      <AlertBanner incidents={data.incidents} onSelectRoom={setSelectedRoomId} />
      <StatusCards summary={data.summary} breakdown={breakdown} onCardClick={setOpenCard} />

      <div style={{ display: "grid", gridTemplateColumns: "220px 1fr 320px", gap: 16, alignItems: "start" }}>
        <FloorSidebar floors={data.floors} selectedFloor={selectedFloor} onSelectFloor={setSelectedFloor} rooms={data.rooms} />

        <div className="glass-panel" style={{ padding: 18 }}>
          <BuildingMap rooms={filteredRooms} selectedRoomId={selectedRoomId} onSelectRoom={setSelectedRoomId} allRooms={data.rooms} selectedFloor={selectedFloor} routePath={routePath} />
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <ActiveIncidentPanel incident={selectedIncident} onAcknowledge={handleAcknowledge} onResolve={handleResolve} />
          <LifecycleStepper incident={selectedIncident} />
          <LiveTrend rooms={data.rooms} roomId={selectedIncident ? selectedIncident.room_id : selectedRoomId} />
          <RecommendedAction
            team={assignedTeam}
            teams={data.teams}
            incident={selectedIncident}
            showToast={showToast}
            onNavigated={loadAll}
          />
          <ForecastPanel refreshKey={routeKey + ":" + data.rooms.map((r) => r.risk_level + r.temperature).join("")} onSelectRoom={setSelectedRoomId} />
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 16 }}>
        <OccupantChart occupants={data.occupants} />
        <RescueTeamsPanel teams={data.teams} />
        <MedicalPanel units={data.medical} />
        <IncidentTimeline events={data.timeline} />
      </div>

      {openCard && (
        <CardDetailModal
          type={openCard}
          incidents={data.incidents}
          occupants={data.occupants}
          medical={data.medical}
          onClose={() => setOpenCard(null)}
          onSelectRoom={(roomId) => {
            setSelectedRoomId(roomId);
            setSelectedFloor(null);
            setOpenCard(null);
          }}
        />
      )}
    </div>
  );
}
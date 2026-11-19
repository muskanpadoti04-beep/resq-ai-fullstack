import React, { useEffect, useState } from "react";
import FloorSidebar from "../components/FloorSidebar.jsx";
import BuildingMap from "../components/BuildingMap.jsx";
import { Loading, ErrorState, RiskPill, fmtNum } from "../components/Common.jsx";
import { getFloors, getRooms } from "../api/client.js";

export default function BuildingPage() {
  const [floors, setFloors] = useState([]);
  const [rooms, setRooms] = useState([]);
  const [selectedFloor, setSelectedFloor] = useState(null);
  const [selectedRoomId, setSelectedRoomId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const load = async () => {
    try {
      const [f, r] = await Promise.all([getFloors(), getRooms()]);
      setFloors(f);
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

  const filteredRooms = selectedFloor === null ? rooms : rooms.filter((r) => r.floor_number === selectedFloor);
  const selectedRoom = rooms.find((r) => r.room_id === selectedRoomId);

  return (
    <div className="fade-in" style={{ display: "grid", gridTemplateColumns: "220px 1fr 260px", gap: 16, alignItems: "start" }}>
      <FloorSidebar floors={floors} selectedFloor={selectedFloor} onSelectFloor={setSelectedFloor} rooms={rooms} />
      <div className="glass-panel" style={{ padding: 18 }}>
        <BuildingMap rooms={filteredRooms} selectedRoomId={selectedRoomId} onSelectRoom={setSelectedRoomId} allRooms={rooms} selectedFloor={selectedFloor} />
      </div>
      <div className="glass-panel" style={{ padding: 18 }}>
        <h3 style={{ marginTop: 0, fontSize: 14 }}>Room Detail</h3>
        {selectedRoom ? (
          <div style={{ fontSize: 12.5, display: "flex", flexDirection: "column", gap: 8 }}>
            <div><b>Room:</b> {selectedRoom.room_id}</div>
            <div><b>Floor:</b> {selectedRoom.floor_number}</div>
            <div><b>Capacity:</b> {selectedRoom.capacity}</div>
            <div><b>Occupants:</b> {selectedRoom.occupants_count}</div>
            <div><b>Temperature:</b> {fmtNum(selectedRoom.temperature, 1, "°C")}</div>
            <div><b>Smoke Level:</b> {fmtNum(selectedRoom.smoke_level, 0, "%")}</div>
            <div><b>Fire Status:</b> {selectedRoom.fire_status}</div>
            <div style={{ marginTop: 4 }}><RiskPill level={selectedRoom.risk_level} /></div>
          </div>
        ) : (
          <p style={{ color: "var(--text-muted)", fontSize: 12.5 }}>Select a room on the map to view details.</p>
        )}
      </div>
    </div>
  );
}

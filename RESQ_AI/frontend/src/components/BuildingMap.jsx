import React, { useState, useEffect, Suspense, lazy } from "react";
import { Boxes, Grid2x2 } from "lucide-react";
import RoomPlan from "./RoomPlan.jsx";

const Building3D = lazy(() => import("./Building3D.jsx"));

export default function BuildingMap({ rooms, selectedRoomId, onSelectRoom, allRooms, selectedFloor = null, routePath = null }) {
  const [viewMode, setViewMode] = useState("2D");

  // When a fire is simulated, jump to the 3D building so the fire is visible there
  useEffect(() => {
    const show3D = () => setViewMode("3D");
    window.addEventListener("resq:fire", show3D);
    return () => window.removeEventListener("resq:fire", show3D);
  }, []);

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "flex-end", alignItems: "center", marginBottom: 14, flexWrap: "wrap", gap: 8 }}>
        <div style={{ display: "flex", gap: 4 }}>
          {[{ id: "3D", icon: Boxes, label: "3D View" }, { id: "2D", icon: Grid2x2, label: "2D Plan" }].map(({ id, icon: Icon, label }) => (
            <button
              key={id}
              onClick={() => setViewMode(id)}
              className="btn"
              style={{
                background: viewMode === id ? "rgba(34,211,238,0.2)" : "transparent",
                display: "flex", alignItems: "center", gap: 5,
              }}
            >
              <Icon size={13} /> {label}
            </button>
          ))}
        </div>
      </div>

      {viewMode === "3D" ? (
        <Suspense fallback={<div style={{ padding: 24, color: "var(--text-muted)", fontSize: 13 }}>Loading 3D building…</div>}>
          <Building3D
            rooms={allRooms || rooms}
            selectedRoomId={selectedRoomId}
            selectedFloor={selectedFloor}
            onSelectRoom={onSelectRoom}
            routePath={routePath}
          />
        </Suspense>
      ) : (
        <RoomPlan rooms={rooms} selectedRoomId={selectedRoomId} onSelectRoom={onSelectRoom} />
      )}
    </div>
  );
}
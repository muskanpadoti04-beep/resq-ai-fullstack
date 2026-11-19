import React from "react";

const FLOOR_NAME = { 1: "Ground floor", 2: "1st floor", 3: "2nd floor", 4: "3rd floor" };

// false = top floor on the left (as in the preview). true = ground floor on the left.
const GROUND_FIRST = false;

// One clear status per room. Quiet rooms stay quiet; only trouble gets colour.
function statusOf(r) {
  if (r.fire_status === "active") return { key: "FIRE", label: "FIRE", colour: "#ff3b30", alarm: true };
  if (r.risk_level === "Critical") return { key: "CRITICAL", label: "CRITICAL", colour: "#ff3b30", alarm: true };
  if (r.risk_level === "High Risk") return { key: "HIGH", label: "HIGH RISK", colour: "#ff9f0a", alarm: true };
  if (r.risk_level === "Moderate") return { key: "WATCH", label: "WATCH", colour: "#ffd60a", alarm: false };
  return { key: "SAFE", label: "SAFE", colour: "#30d158", alarm: false };
}

// "4B-203" -> "B"
const wingOf = (r) => {
  const m = String(r.room_id).match(/^\d+([A-Za-z])/);
  return m ? m[1].toUpperCase() : "A";
};
const byRoom = (a, b) =>
  String(a.room_number ?? a.room_id).localeCompare(String(b.room_number ?? b.room_id), undefined, { numeric: true });

function RoomTile({ room, selected, onSelect, door }) {
  const st = statusOf(room);
  const noSignal = room.sensor_status && room.sensor_status !== "ok";
  const people = room.occupants_count || 0;
  return (
    <button
      type="button"
      onClick={() => onSelect && onSelect(room.room_id)}
      className={st.key === "FIRE" ? "resq-banner-fire" : ""}
      title={`${room.room_id} · ${st.label}${noSignal ? " · sensor data old or missing" : ""}`}
      style={{
        position: "relative", width: "100%", minHeight: 84, textAlign: "left", cursor: "pointer",
        padding: "10px 12px", borderRadius: 10, color: "#fff", font: "inherit",
        background: st.alarm ? `${st.colour}26` : "rgba(255,255,255,0.04)",
        border: selected
          ? "2px solid #fff"
          : `${st.alarm ? 2 : 1}px ${noSignal ? "dashed" : "solid"} ${st.alarm ? st.colour : "rgba(255,255,255,0.18)"}`,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontSize: 16, fontWeight: 800 }}>{st.key === "FIRE" ? "🔥 " : ""}{room.room_id}</span>
        {!st.alarm && <span style={{ width: 9, height: 9, borderRadius: "50%", background: st.colour }} />}
      </div>

      {st.alarm ? (
        <>
          <div style={{ fontSize: 13, fontWeight: 800, color: st.colour, marginTop: 4 }}>{st.label}</div>
          <div style={{ fontSize: 13, marginTop: 3 }}>{room.temperature ?? "–"}°C · smoke {room.smoke_level ?? "–"}%</div>
          <div style={{ fontSize: 13, marginTop: 3, fontWeight: people > 0 ? 700 : 400, color: people > 0 ? "#fff" : "var(--text-muted)" }}>
            {people > 0 ? `👥 ${people} inside` : "empty"}
          </div>
        </>
      ) : (
        <div style={{ fontSize: 13, marginTop: 6, color: "var(--text-muted)" }}>
          {room.temperature ?? "–"}°C{people > 0 ? ` · 👥 ${people}` : ""}
        </div>
      )}

      {noSignal && (
        <div style={{ fontSize: 11, marginTop: 5, color: "#ffb020", fontWeight: 700 }}>
          ⚠ {room.sensor_status === "missing" ? "no sensor data" : "old data"}
        </div>
      )}

      {/* door onto the corridor */}
      <span
        style={{
          position: "absolute", left: "50%", marginLeft: -15, width: 30, height: 6, borderRadius: 2,
          background: "#0b1220", border: "1px solid rgba(255,255,255,0.35)",
          ...(door === "down" ? { bottom: -9 } : { top: -9 }),
        }}
      />
    </button>
  );
}

// Drop-in replacement for the 2D room grid. Same prop names as BuildingMap uses.
export default function RoomPlan({ rooms, selectedRoomId, onSelectRoom }) {
  const list = rooms || [];
  const count = (fn) => list.filter(fn).length;
  const fire = count((r) => statusOf(r).key === "FIRE");
  const critical = count((r) => statusOf(r).key === "CRITICAL");
  const high = count((r) => statusOf(r).key === "HIGH");
  const noSignal = count((r) => r.sensor_status && r.sensor_status !== "ok");
  const safe = count((r) => statusOf(r).key === "SAFE" || statusOf(r).key === "WATCH");

  const floors = [...new Set(list.map((r) => r.floor_number))].sort((a, b) => (GROUND_FIRST ? a - b : b - a));
  const chip = (colour, text) => (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 14, fontWeight: 700 }}>
      <span style={{ width: 11, height: 11, borderRadius: "50%", background: colour }} />{text}
    </span>
  );

  const wingName = { fontSize: 11, fontWeight: 700, letterSpacing: 1.2, color: "var(--text-muted)", margin: "0 0 6px 2px" };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16, minWidth: 0 }}>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 18, padding: "8px 2px" }}>
        {chip("#ff3b30", `${fire} on fire`)}
        {chip("#ff3b30", `${critical} critical`)}
        {chip("#ff9f0a", `${high} high risk`)}
        {chip("#30d158", `${safe} safe`)}
        {noSignal > 0 && <span style={{ fontSize: 14, fontWeight: 700, color: "#ffb020" }}>⚠ {noSignal} with old sensor data</span>}
      </div>

      {/* 2 floors per row: top two floors on the first row, next two below */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 14, alignItems: "start" }}>
        {floors.map((fl) => {
          const fr = list.filter((r) => r.floor_number === fl).sort(byRoom);
          const wings = [...new Set(fr.map(wingOf))].sort();
          const floorFire = fr.filter((r) => r.fire_status === "active").length;

          return (
            <section
              key={fl}
              aria-label={FLOOR_NAME[fl] || `Floor ${fl}`}
              style={{
                minWidth: 0, padding: 12, borderRadius: 12,
                background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.14)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 12, gap: 8 }}>
                <span style={{ fontSize: 13, fontWeight: 800, letterSpacing: 0.6, color: "#fff" }}>
                  {(FLOOR_NAME[fl] || `Floor ${fl}`).toUpperCase()}
                </span>
                <span style={{ fontSize: 12, fontWeight: 600, color: floorFire ? "#ff6b61" : "var(--text-muted)" }}>
                  {floorFire ? `${floorFire} on fire` : "No fire"}
                </span>
              </div>

              {wings.map((w, i) => (
                <React.Fragment key={w}>
                  {i > 0 && (
                    <div
                      style={{
                        height: 28, margin: "18px 0 16px", borderRadius: 6,
                        background: "rgba(255,255,255,0.03)", border: "1px dashed rgba(255,255,255,0.22)",
                        display: "flex", alignItems: "center", justifyContent: "center",
                        fontSize: 11, letterSpacing: 3, color: "var(--text-muted)",
                      }}
                    >
                      CORRIDOR
                    </div>
                  )}
                  <div style={wingName}>WING {w}</div>
                  <div style={{ display: "grid", gap: 12, gridTemplateColumns: "repeat(2, minmax(0, 1fr))" }}>
                    {fr.filter((r) => wingOf(r) === w).map((r) => (
                      <RoomTile
                        key={r.room_id}
                        room={r}
                        selected={r.room_id === selectedRoomId}
                        onSelect={onSelectRoom}
                        door={i === 0 ? "down" : "up"}
                      />
                    ))}
                  </div>
                </React.Fragment>
              ))}
            </section>
          );
        })}
      </div>
    </div>
  );
}
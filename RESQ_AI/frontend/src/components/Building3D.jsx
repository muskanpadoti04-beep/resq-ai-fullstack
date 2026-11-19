import React, { useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Html, Edges, Line } from "@react-three/drei";
import { useMapLayers } from "../mapLayers.js";

/**
 * Interactive 3D building (React Three Fiber).
 * Every colour / fire / smoke / label comes from the rooms returned by the backend API.
 *  - Click a floor / room -> floor details popup opens on that floor block
 *  - Click a room         -> onSelectRoom(room_id)
 *  - Double-click a room  -> onOpen2D(room)   (opens the 2D plan on that floor)
 *  - Drag = rotate, scroll = zoom
 */

const FLOOR_GAP = 1.7;
const PLATE = { w: 12.6, d: 7.4, h: 0.14 };
const ROOM = { w: 3.4, h: 1.0, d: 2.7 };

const RISK = {
  Critical: { color: "#ff3b30", glow: 0.9 },
  "High Risk": { color: "#ffb020", glow: 0.55 },
  Moderate: { color: "#2f8cff", glow: 0.3 },
  Safe: { color: "#22e6a3", glow: 0.25 },
};
const RISK_RANK = { Critical: 0, "High Risk": 1, Moderate: 2, Safe: 3 };

const floorLabel = (n) => {
  if (n === 1) return "Ground Floor";
  const k = n - 1;
  const suffix = k === 1 ? "st" : k === 2 ? "nd" : k === 3 ? "rd" : "th";
  return `${k}${suffix} Floor`;
};

// 3 columns x 2 rows of rooms on every floor
function roomPosition(index, floorNumber) {
  const col = index % 3;
  const row = Math.floor(index / 3);
  const y = (floorNumber - 1) * FLOOR_GAP + PLATE.h / 2 + ROOM.h / 2 + 0.05;
  return [(col - 1) * 3.9, y, row === 0 ? -1.75 : 1.75];
}

/**
 * Which burning room should the rescue route go to?
 * 1) the selected room, if it is on fire
 * 2) otherwise the most severe fire (risk level, then smoke, then temperature)
 * The backend never closes old fires, so we never just take "the first one".
 */
function pickRescueTarget(rooms, selectedRoomId) {
  const fires = rooms.filter((r) => r.fire_status === "active");
  if (!fires.length) return { fires, target: null };
  const selected = fires.find((r) => r.room_id === selectedRoomId);
  if (selected) return { fires, target: selected };
  const sorted = [...fires].sort(
    (a, b) =>
      (RISK_RANK[a.risk_level] ?? 9) - (RISK_RANK[b.risk_level] ?? 9) ||
      (b.smoke_level || 0) - (a.smoke_level || 0) ||
      (b.temperature || 0) - (a.temperature || 0)
  );
  return { fires, target: sorted[0] };
}

const labelStyle = {
  padding: "2px 6px", borderRadius: 6, whiteSpace: "nowrap", textAlign: "center",
  background: "rgba(6,12,23,0.78)", border: "1px solid rgba(34,211,238,0.35)",
  color: "#eaf4ff", fontSize: 11, lineHeight: 1.25, fontWeight: 700,
};

// A few small puffs that drift up and fade, instead of one big grey ball
function Smoke({ level }) {
  const refs = useRef([]);
  const puffs = useMemo(
    () => [
      { ox: -0.6, oz: -0.4, phase: 0.0, r: 0.24 },
      { ox: 0.5, oz: -0.2, phase: 0.27, r: 0.3 },
      { ox: -0.2, oz: 0.5, phase: 0.55, r: 0.26 },
      { ox: 0.6, oz: 0.4, phase: 0.8, r: 0.22 },
    ],
    []
  );
  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    refs.current.forEach((m, i) => {
      if (!m) return;
      const p = puffs[i];
      const k = (t * 0.22 + p.phase) % 1;
      m.position.set(p.ox + Math.sin(t + i) * 0.1, k * 1.7, p.oz);
      m.scale.setScalar((0.6 + k * 1.3) * (0.6 + level / 100));
      m.material.opacity = (1 - k) * Math.min(0.4, level / 220);
    });
  });
  return (
    <group position={[0, ROOM.h / 2, 0]}>
      {puffs.map((p, i) => (
        <mesh key={i} ref={(el) => (refs.current[i] = el)}>
          <sphereGeometry args={[p.r, 12, 12]} />
          <meshBasicMaterial color="#aab6c6" transparent opacity={0.2} depthWrite={false} />
        </mesh>
      ))}
    </group>
  );
}

// ---- Risk heatmap: temperature + smoke -> green / yellow / red --------------------------------
const lerpHex = (a, b, t) => {
  const pa = [1, 3, 5].map((i) => parseInt(a.slice(i, i + 2), 16));
  const pb = [1, 3, 5].map((i) => parseInt(b.slice(i, i + 2), 16));
  return "#" + pa.map((v, i) => Math.round(v + (pb[i] - v) * t).toString(16).padStart(2, "0")).join("");
};
const HEAT_STOPS = ["#22e6a3", "#ffd23f", "#ff8a1f", "#ff3b30"];
const heatScale = (t) => {
  const x = Math.min(1, Math.max(0, t)) * (HEAT_STOPS.length - 1);
  const i = Math.min(HEAT_STOPS.length - 2, Math.floor(x));
  return lerpHex(HEAT_STOPS[i], HEAT_STOPS[i + 1], x - i);
};
const heatScore = (room) =>
  Math.max(((room.temperature || 20) - 22) / 65, (room.smoke_level || 0) / 100);

// ---- Occupants: small people figures standing inside the room ---------------------------------
function Occupants({ count, color }) {
  const n = Math.min(Math.max(0, Math.round(count || 0)), 6);
  const spots = [
    [-1.1, -0.7], [0, -0.7], [1.1, -0.7], [-1.1, 0.7], [0, 0.7], [1.1, 0.7],
  ];
  const floorY = -ROOM.h / 2;
  return (
    <group>
      {spots.slice(0, n).map(([x, z], i) => (
        <group key={i} position={[x, floorY, z]}>
          <mesh position={[0, 0.17, 0]}>
            <cylinderGeometry args={[0.07, 0.09, 0.34, 8]} />
            <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.6} />
          </mesh>
          <mesh position={[0, 0.42, 0]}>
            <sphereGeometry args={[0.075, 10, 10]} />
            <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.6} />
          </mesh>
        </group>
      ))}
    </group>
  );
}

// ---- Sensor: small blinking node on the ceiling, colour follows the room temperature ----------
function Sensor({ room }) {
  const ref = useRef();
  const color = heatScore(room) > 0.55 ? "#ff3b30" : heatScore(room) > 0.25 ? "#ffb020" : "#22d3ee";
  useFrame(({ clock }) => {
    if (ref.current) ref.current.emissiveIntensity = 0.9 + 0.7 * Math.sin(clock.getElapsedTime() * 3);
  });
  return (
    <group position={[ROOM.w / 2 - 0.35, ROOM.h / 2 - 0.06, ROOM.d / 2 - 0.35]}>
      <mesh>
        <sphereGeometry args={[0.1, 12, 12]} />
        <meshStandardMaterial ref={ref} color={color} emissive={color} emissiveIntensity={1} />
      </mesh>
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.16, 0.19, 24]} />
        <meshBasicMaterial color={color} transparent opacity={0.7} side={2} />
      </mesh>
    </group>
  );
}

// ---- CCTV camera: body + lens, mounted in a top corner, with a tiny red record LED ------------
function Camera() {
  return (
    <group position={[-ROOM.w / 2 + 0.3, ROOM.h / 2 - 0.1, -ROOM.d / 2 + 0.3]} rotation={[0.5, 0.8, 0]}>
      <mesh>
        <boxGeometry args={[0.2, 0.14, 0.34]} />
        <meshStandardMaterial color="#cfd8e3" roughness={0.4} metalness={0.5} />
      </mesh>
      <mesh position={[0, 0, 0.2]} rotation={[Math.PI / 2, 0, 0]}>
        <cylinderGeometry args={[0.06, 0.08, 0.1, 10]} />
        <meshStandardMaterial color="#0b1220" />
      </mesh>
      <mesh position={[0.07, 0.09, -0.1]}>
        <sphereGeometry args={[0.03, 8, 8]} />
        <meshBasicMaterial color="#ff3b30" />
      </mesh>
    </group>
  );
}

function Room({ room, position, dimmed, selected, layers, onSelect, onOpen2D, showLabel = true }) {
  const risk = RISK[room.risk_level] || RISK.Safe;
  // Risk Heatmap layer re-colours every room by temperature / smoke instead of risk level
  const tint = layers.heatmap ? heatScale(heatScore(room)) : risk.color;
  const mat = useRef();
  const flame = useRef();
  const [hover, setHover] = useState(false);
  const onFire = room.fire_status === "active";
  const smoke = room.smoke_level || 0;
  const showDetail = hover || selected;
  const showFire = layers.fire && !dimmed;

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    if (mat.current) {
      const base = risk.glow * (dimmed ? 0.35 : 1);
      mat.current.emissiveIntensity =
        base + (onFire && layers.fire ? 0.35 * Math.sin(t * 5) : 0) + (selected ? 0.35 : 0) + (hover ? 0.2 : 0);
    }
    if (flame.current) {
      const s = 1 + 0.18 * Math.sin(t * 9);
      flame.current.scale.set(s, 1 + 0.25 * Math.sin(t * 7 + 1), s);
    }
  });

  return (
    <group position={position}>
      <mesh
        onClick={(e) => { e.stopPropagation(); onSelect(room.room_id); }}
        onDoubleClick={(e) => { e.stopPropagation(); onOpen2D && onOpen2D(room); }}
        onPointerOver={(e) => { e.stopPropagation(); setHover(true); document.body.style.cursor = "pointer"; }}
        onPointerOut={() => { setHover(false); document.body.style.cursor = "auto"; }}
      >
        <boxGeometry args={[ROOM.w, ROOM.h, ROOM.d]} />
        <meshStandardMaterial
          ref={mat} color={tint} emissive={tint} roughness={0.35} metalness={0.2}
          transparent opacity={dimmed ? 0.18 : selected ? 0.85 : layers.heatmap ? 0.7 : 0.55} depthWrite={false}
        />
        <Edges color={selected ? "#ffffff" : tint} />
      </mesh>

      {layers.occupants && !dimmed && (
        <Occupants count={room.occupants_count} color={onFire || room.risk_level === "Critical" ? "#ffd23f" : "#22e6a3"} />
      )}
      {layers.sensors && !dimmed && <Sensor room={room} />}
      {layers.cameras && !dimmed && <Camera />}

      {onFire && showFire && (
        <>
          <mesh ref={flame} position={[0, 0.2, 0]}>
            <coneGeometry args={[0.5, 1.1, 10]} />
            <meshStandardMaterial color="#ff6a1a" emissive="#ff3b00" emissiveIntensity={1.6} transparent opacity={0.9} />
          </mesh>
          <pointLight color="#ff4b1f" intensity={6} distance={5} position={[0, 0.6, 0]} />
        </>
      )}

      {smoke >= 40 && showFire && <Smoke level={smoke} />}

      {!dimmed && showLabel && (
        <Html
          position={[0, ROOM.h / 2 + 0.4, 0]}
          center
          distanceFactor={9}
          zIndexRange={showDetail ? [100, 90] : [20, 0]}
          style={{ pointerEvents: "none" }}
        >
          <div
            style={{
              ...labelStyle,
              borderColor: tint,
              padding: showDetail ? "2px 6px" : "1px 5px",
              fontSize: showDetail ? 11 : 10,
              opacity: showDetail ? 1 : 0.85,
            }}
          >
            {room.room_id}
            {showDetail && (
              <div style={{ fontSize: 9.5, fontWeight: 500, color: tint }}>
                {layers.occupants ? `${room.occupants_count} people · ` : ""}
                {layers.heatmap ? `${Math.round(room.temperature || 0)}°C · ${Math.round(smoke)}% smoke` : room.risk_level}
              </div>
            )}
          </div>
        </Html>
      )}
    </group>
  );
}

// ---- Floor details panel: covers the whole 3D box (DOM overlay, not inside the 3D scene) -----
function FloorPanel({ floorNumber, list, onClose, onSelectRoom }) {
  const s = useMemo(() => {
    const worst = [...list].sort(
      (a, b) => (RISK_RANK[a.risk_level] ?? 9) - (RISK_RANK[b.risk_level] ?? 9)
    )[0];
    return {
      people: list.reduce((n, r) => n + (r.occupants_count || 0), 0),
      fires: list.filter((r) => r.fire_status === "active").length,
      temp: Math.max(0, ...list.map((r) => r.temperature || 0)),
      smoke: Math.max(0, ...list.map((r) => r.smoke_level || 0)),
      risk: worst?.risk_level || "Safe",
    };
  }, [list]);

  const c = (RISK[s.risk] || RISK.Safe).color;
  const box = {
    background: "rgba(6,12,23,0.9)", border: "1px solid rgba(34,211,238,0.25)",
    borderRadius: 10, padding: "8px 12px",
  };
  const items = [
    ["Occupants", s.people], ["Active fires", s.fires],
    ["Max temp", `${Math.round(s.temp)}°C`], ["Max smoke", `${Math.round(s.smoke)}%`],
  ];

  return (
    <div
      style={{
        position: "absolute", inset: 10, zIndex: 1000, display: "flex", flexDirection: "column", gap: 12,
        padding: 16, borderRadius: 12, overflow: "auto", color: "#eaf4ff", fontSize: 12,
        background: "rgba(8,16,30,0.94)", backdropFilter: "blur(4px)", border: `1px solid ${c}`,
        boxShadow: "0 10px 40px rgba(0,0,0,.55)",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{ fontSize: 20, fontWeight: 800 }}>{floorLabel(floorNumber)}</div>
          <span style={{ padding: "2px 12px", borderRadius: 20, background: c + "33", color: c, fontWeight: 700 }}>
            {s.risk}
          </span>
        </div>
        <button
          onClick={onClose}
          aria-label="Close"
          style={{ background: "none", border: 0, color: "#8da2c4", fontSize: 26, cursor: "pointer", lineHeight: 1 }}
        >
          ×
        </button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(110px, 1fr))", gap: 8 }}>
        {items.map(([k, v]) => (
          <div key={k} style={box}>
            <div style={{ fontSize: 10, color: "#8da2c4" }}>{k.toUpperCase()}</div>
            <b style={{ fontSize: 20 }}>{v}</b>
          </div>
        ))}
      </div>

      <div style={{ color: "#8da2c4", fontSize: 11 }}>ROOMS ({list.length})</div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(170px, 1fr))", gap: 8 }}>
        {list.map((r) => {
          const rc = (RISK[r.risk_level] || RISK.Safe).color;
          const fire = r.fire_status === "active";
          return (
            <div
              key={r.room_id}
              onClick={() => onSelectRoom(r.room_id)}
              style={{ ...box, cursor: "pointer", borderColor: rc, padding: "10px 12px" }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <b style={{ fontSize: 14 }}>{r.room_id}</b>
                <span style={{ color: rc, fontWeight: 700 }}>{fire ? "FIRE" : r.risk_level}</span>
              </div>
              <div style={{ marginTop: 6, color: "#b9c8e0", lineHeight: 1.6 }}>
                {r.occupants_count || 0} people<br />
                {Math.round(r.temperature || 0)}°C · {Math.round(r.smoke_level || 0)}% smoke
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function FloorPlate({ floorNumber, highlighted, dimmed, onClick, showLabel = true }) {
  return (
    <group position={[0, (floorNumber - 1) * FLOOR_GAP, 0]}>
      <mesh
        onClick={(e) => { e.stopPropagation(); onClick && onClick(); }}
        onPointerOver={(e) => { e.stopPropagation(); document.body.style.cursor = "pointer"; }}
        onPointerOut={() => { document.body.style.cursor = "auto"; }}
      >
        <boxGeometry args={[PLATE.w, PLATE.h, PLATE.d]} />
        <meshStandardMaterial color="#0b2a4a" roughness={0.2} metalness={0.4} transparent opacity={dimmed ? 0.15 : 0.55} depthWrite={false} />
        <Edges color={highlighted ? "#22d3ee" : "#1b6fa0"} />
      </mesh>
      {showLabel && (
        <Html position={[-PLATE.w / 2 - 0.2, 0.25, PLATE.d / 2 + 0.2]} center distanceFactor={9} style={{ pointerEvents: "none" }}>
          <div style={{ ...labelStyle, color: highlighted ? "#22d3ee" : "#9fb0c8", borderColor: highlighted ? "#22d3ee" : "rgba(34,211,238,0.25)" }}>
            {floorLabel(floorNumber)}
          </div>
        </Html>
      )}
    </group>
  );
}

// Road running alongside the building, with dashed centre-line markings
function Road({ z = -6.4, length = 30, width = 3 }) {
  const dashCount = 14;
  const dashW = 1.0;
  const gap = length / dashCount;
  return (
    <group position={[0, 0, z]}>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.1, 0]}>
        <planeGeometry args={[length, width]} />
        <meshStandardMaterial color="#121c2c" roughness={0.9} />
      </mesh>
      {Array.from({ length: dashCount }).map((_, i) => (
        <mesh
          key={i}
          rotation={[-Math.PI / 2, 0, 0]}
          position={[-length / 2 + gap * i + gap / 2, -0.095, 0]}
        >
          <planeGeometry args={[dashW, 0.1]} />
          <meshStandardMaterial color="#cfd8e3" />
        </mesh>
      ))}
    </group>
  );
}

// A simple low-poly tree: trunk + two leaf cones
function Tree({ x, z, scale = 1 }) {
  return (
    <group position={[x, -0.1, z]} scale={scale}>
      <mesh position={[0, 0.3, 0]}>
        <cylinderGeometry args={[0.07, 0.1, 0.6, 6]} />
        <meshStandardMaterial color="#3a2a1a" roughness={0.9} />
      </mesh>
      <mesh position={[0, 0.85, 0]}>
        <coneGeometry args={[0.45, 0.9, 8]} />
        <meshStandardMaterial color="#1f9d6b" emissive="#114d34" emissiveIntensity={0.3} roughness={0.8} />
      </mesh>
      <mesh position={[0, 1.25, 0]}>
        <coneGeometry args={[0.33, 0.7, 8]} />
        <meshStandardMaterial color="#22e6a3" emissive="#114d34" emissiveIntensity={0.3} roughness={0.8} />
      </mesh>
    </group>
  );
}

// Road + a line of trees on the far side, so the building sits in a small street scene
function CityScene() {
  const treeX = [-11, -7.5, -4, 8, 11, 13.5];
  return (
    <group>
      <Road />
      {treeX.map((x, i) => (
        <Tree key={i} x={x} z={-8.2} scale={0.9 + (i % 3) * 0.12} />
      ))}
    </group>
  );
}

function Stair({ x, name, blocked, height, showLabel = true }) {
  const color = blocked ? "#ff3b30" : "#22e6a3";
  return (
    <group position={[x, height / 2 - 0.3, 0]}>
      <mesh>
        <boxGeometry args={[1.0, height, 1.6]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.35} transparent opacity={0.3} depthWrite={false} />
        <Edges color={color} />
      </mesh>
      {showLabel && (
        <Html position={[0, height / 2 + 0.55, 0]} center distanceFactor={9} style={{ pointerEvents: "none" }}>
          <div style={{ ...labelStyle, borderColor: color, color }}>
            {name} · {blocked ? "Blocked" : "Available"}
          </div>
        </Html>
      )}
    </group>
  );
}

function Scene({
  rooms, selectedRoomId, selectedFloor, layers, onSelectRoom, onOpen2D,
  popupFloor, onFloorClick,
}) {
  const { floors, maxFloor, fireRoom, stairABlocked } = useMemo(() => {
    const byFloor = {};
    rooms.forEach((r) => { (byFloor[r.floor_number] = byFloor[r.floor_number] || []).push(r); });
    const nums = Object.keys(byFloor).map(Number).sort((a, b) => a - b);
    Object.values(byFloor).forEach((list) => list.sort((a, b) => a.room_id.localeCompare(b.room_id)));
    const { fires, target } = pickRescueTarget(rooms, selectedRoomId);
    return { floors: nums.map((n) => ({ n, list: byFloor[n] })), maxFloor: nums[nums.length - 1] || 1, fireRoom: target, stairABlocked: fires.length > 0 };
  }, [rooms, selectedRoomId]);

  // Rescue route: main entrance -> Stair B -> corridor -> burning room
  const route = useMemo(() => {
    if (!fireRoom) return null;
    const idx = (floors.find((f) => f.n === fireRoom.floor_number)?.list || []).findIndex((r) => r.room_id === fireRoom.room_id);
    if (idx < 0) return null;
    const [tx, , tz] = roomPosition(idx, fireRoom.floor_number);
    const y = (fireRoom.floor_number - 1) * FLOOR_GAP + 0.3;
    return [[7.0, 0.3, 4.4], [7.0, 0.3, 0], [7.0, y, 0], [tx, y, 0], [tx, y, tz]];
  }, [fireRoom, floors]);

  // Blocked route: Stair A -> corridor -> burning room (cut off by the fire)
  const blockedRoute = useMemo(() => {
    if (!fireRoom) return null;
    const idx = (floors.find((f) => f.n === fireRoom.floor_number)?.list || []).findIndex((r) => r.room_id === fireRoom.room_id);
    if (idx < 0) return null;
    const [tx, , tz] = roomPosition(idx, fireRoom.floor_number);
    const y = (fireRoom.floor_number - 1) * FLOOR_GAP + 0.45;
    return [[-7.0, 0.45, 4.4], [-7.0, 0.45, 0], [-7.0, y, 0], [tx, y, 0], [tx, y, tz]];
  }, [fireRoom, floors]);

  const height = maxFloor * FLOOR_GAP;
  // hide all 3D text labels while the floor details panel is open
  const showLabel = popupFloor === null;

  return (
    <>
      <ambientLight intensity={0.7} />
      <directionalLight position={[8, 14, 6]} intensity={1.1} />
      <directionalLight position={[-8, 6, -6]} intensity={0.35} color="#22d3ee" />

      <gridHelper args={[36, 36, "#0e4a6b", "#0a2a40"]} position={[0, -0.12, 0]} />

      <CityScene />

      {floors.map(({ n, list }) => {
        const dimmed = selectedFloor !== null && n !== selectedFloor;
        return (
          <group key={n}>
            <FloorPlate
              floorNumber={n}
              highlighted={selectedFloor === n || popupFloor === n}
              dimmed={dimmed}
              onClick={() => onFloorClick(n)}
              showLabel={showLabel}
            />
            {list.map((room, i) => (
              <Room
                key={room.room_id}
                room={room}
                position={roomPosition(i, n)}
                dimmed={dimmed}
                selected={room.room_id === selectedRoomId}
                layers={layers}
                onSelect={(id) => { onSelectRoom(id); onFloorClick(n); }}
                onOpen2D={onOpen2D}
                showLabel={showLabel}
              />
            ))}
          </group>
        );
      })}

      {/* a blocked stair belongs to the Blocked Routes layer, an open stair to Rescue Routes */}
      {(stairABlocked ? layers.blocked : layers.routes) && (
        <Stair x={-7.0} name="Stair A" blocked={stairABlocked} height={height} showLabel={showLabel} />
      )}
      {layers.routes && <Stair x={7.0} name="Stair B" blocked={false} height={height} showLabel={showLabel} />}

      {layers.routes && route && (
        <Line points={route} color="#22e6a3" lineWidth={3} dashed dashSize={0.4} gapSize={0.25} />
      )}
      {layers.blocked && blockedRoute && (
        <Line points={blockedRoute} color="#ff3b30" lineWidth={3} dashed dashSize={0.25} gapSize={0.25} />
      )}

      <OrbitControls
        target={[0, Math.max(1.6, height / 2 - 0.4), 0]}
        enableDamping
        minDistance={10}
        maxDistance={34}
        maxPolarAngle={Math.PI / 2.05}
      />
    </>
  );
}

class Boundary extends React.Component {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    if (this.state.failed) {
      return (
        <div style={{ padding: 24, color: "var(--text-muted)", fontSize: 13 }}>
          3D view could not start on this device (WebGL unavailable). Please use the 2D Plan.
        </div>
      );
    }
    return this.props.children;
  }
}

const LEGEND = [
  ["Critical", "#ff3b30"], ["High Risk", "#ffb020"], ["Moderate", "#2f8cff"], ["Safe", "#22e6a3"],
];

const hudBox = {
  position: "absolute", padding: "6px 10px", borderRadius: 8,
  background: "rgba(6,12,23,0.75)", border: "1px solid var(--border-subtle)",
  fontSize: 11, color: "#eaf4ff",
};

export default function Building3D({ rooms, selectedRoomId, selectedFloor = null, onSelectRoom, onOpen2D }) {
  const { target } = useMemo(() => pickRescueTarget(rooms, selectedRoomId), [rooms, selectedRoomId]);
  // same state the "Map Layers" switches in the sidebar change
  const layers = useMapLayers();

  // which floor currently shows the details popup
  const [popupFloor, setPopupFloor] = useState(null);
  // choosing a floor from the sidebar list also opens its popup
  useEffect(() => { setPopupFloor(selectedFloor); }, [selectedFloor]);
  const popupRooms = useMemo(
    () => rooms.filter((r) => r.floor_number === popupFloor).sort((a, b) => a.room_id.localeCompare(b.room_id)),
    [rooms, popupFloor]
  );

  return (
    <div
      style={{
        position: "relative", height: 520, borderRadius: 12, overflow: "hidden",
        border: "1px solid var(--border-subtle)",
        background: "radial-gradient(circle at 50% 30%, rgba(34,211,238,0.08), rgba(6,12,23,0.95) 70%)",
      }}
    >
      <Boundary>
        <Canvas
          camera={{ position: [15, 11, 15], fov: 38 }}
          dpr={[1, 2]}
          gl={{ antialias: true, alpha: true }}
          onPointerMissed={() => setPopupFloor(null)}
        >
          <Scene
            rooms={rooms}
            selectedRoomId={selectedRoomId}
            selectedFloor={selectedFloor}
            layers={layers}
            onSelectRoom={onSelectRoom}
            onOpen2D={onOpen2D}
            popupFloor={popupFloor}
            onFloorClick={setPopupFloor}
          />
        </Canvas>
      </Boundary>

      {popupFloor !== null && popupRooms.length > 0 && (
        <FloorPanel
          floorNumber={popupFloor}
          list={popupRooms}
          onClose={() => setPopupFloor(null)}
          onSelectRoom={onSelectRoom}
        />
      )}

      {target && layers.routes && popupFloor === null && (
        <div style={{ ...hudBox, left: 12, top: 12, borderColor: "rgba(34,230,163,0.5)", color: "#22e6a3" }}>
          Rescue route to {target.room_id}
        </div>
      )}

      <div style={{ ...hudBox, left: 12, bottom: 12, display: "flex", flexWrap: "wrap", gap: 10, maxWidth: "55%" }}>
        {layers.heatmap ? (
          <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
            Cool
            <span style={{ width: 90, height: 8, borderRadius: 4, background: `linear-gradient(90deg, ${HEAT_STOPS.join(",")})` }} />
            Hot
          </span>
        ) : (
          LEGEND.map(([name, color]) => (
            <span key={name} style={{ display: "flex", alignItems: "center", gap: 5 }}>
              <span style={{ width: 9, height: 9, borderRadius: 2, background: color }} />
              {name}
            </span>
          ))
        )}
      </div>
      <div style={{ position: "absolute", right: 12, bottom: 12, fontSize: 10.5, color: "var(--text-muted)", textAlign: "right", maxWidth: "40%" }}>
        Drag to rotate · Scroll to zoom · Click floor for details · Double-click room to open 2D
      </div>
    </div>
  );
}
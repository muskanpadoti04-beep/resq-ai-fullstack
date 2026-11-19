import React, { useEffect, useState } from "react";
import NotificationBell from "./NotificationBell.jsx";
import { Wifi, RefreshCw, Flame, LayoutDashboard, Building2, Users, Truck, Stethoscope, BarChart3, FileText } from "lucide-react";

const TAB_ICONS = {
  Dashboard: LayoutDashboard,
  Building: Building2,
  Occupants: Users,
  "Rescue Teams": Truck,
  Medical: Stethoscope,
  Analytics: BarChart3,
  Reports: FileText,
};

const actionBtn = {
  display: "flex", alignItems: "center", gap: 6, borderRadius: 8,
  fontSize: 12, fontWeight: 700, letterSpacing: "0.02em", whiteSpace: "nowrap",
  transition: "all 0.15s ease",
};

function ShieldFlameLogo({ size = 24 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M24 3 L42 9 V22 C42 33 34.5 41.5 24 45 C13.5 41.5 6 33 6 22 V9 Z"
        stroke="#fca5a5"
        strokeWidth="2.4"
        fill="rgba(239,68,68,0.12)"
      />
      <path
        d="M24 13 C22 17 18 19 18 24 C18 28 21 31 24 31 C27 31 30 28 30 24 C30 21 28 20 27.5 18 C27 20 25.5 21 25.5 21 C26 18 24.5 15 24 13 Z"
        fill="#ef4444"
        stroke="#fca5a5"
        strokeWidth="0.6"
      />
    </svg>
  );
}

export default function Navbar({ tabs, activeTab, onTabChange, user, onLogout }) {
  const canOperate = !user || user.role === "operator" || user.role === "admin";
  const [now, setNow] = useState(new Date());
  const [wide, setWide] = useState(typeof window !== "undefined" && window.innerWidth >= 1750);
  const [xwide, setXwide] = useState(typeof window !== "undefined" && window.innerWidth >= 1850);
  const [simulating, setSimulating] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    const onResize = () => {
      setWide(window.innerWidth >= 1750);
      setXwide(window.innerWidth >= 1850);
    };
    const onSimulating = (e) => setSimulating(!!e.detail);
    const onRefreshing = (e) => setRefreshing(!!e.detail);
    window.addEventListener("resize", onResize);
    window.addEventListener("resq:simulating", onSimulating);
    window.addEventListener("resq:refreshing", onRefreshing);
    return () => {
      clearInterval(t);
      window.removeEventListener("resize", onResize);
      window.removeEventListener("resq:simulating", onSimulating);
      window.removeEventListener("resq:refreshing", onRefreshing);
    };
  }, []);

  const dateStr = now.toLocaleDateString(undefined, { day: "2-digit", month: "short", year: "numeric" });
  const timeStr = now.toLocaleTimeString();

  return (
    <header
      className="glass-panel"
      style={{
        borderRadius: 0,
        borderLeft: "none",
        borderRight: "none",
        borderTop: "none",
        position: "sticky",
        top: 0,
        zIndex: 20,
      }}
    >
      {/* 3 columns: logo (left) | tabs (center) | time/status/command center (right) */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: wide ? "1fr auto 1fr" : "auto 1fr auto",
          alignItems: "center",
          padding: "12px 24px",
          gap: 16,
        }}
      >
        {/* LEFT: logo */}
        <div style={{ display: "flex", alignItems: "center", gap: 12, justifySelf: "start" }}>
          <div
            style={{
              width: 40, height: 40, borderRadius: 10,
              background: "linear-gradient(160deg, rgba(239,68,68,0.35), rgba(127,29,29,0.5))",
              display: "flex", alignItems: "center", justifyContent: "center",
              border: "1px solid rgba(239,68,68,0.5)",
              boxShadow: "0 0 14px var(--red-glow)",
              flexShrink: 0,
            }}
          >
            <ShieldFlameLogo size={26} />
          </div>
          <div>
            <div style={{ fontSize: 18, fontWeight: 800, letterSpacing: "0.04em", color: "#fff", whiteSpace: "nowrap" }}>
              RESQ <span style={{ color: "var(--red)" }}>AI</span>
            </div>
            <div style={{ fontSize: 10.5, color: "var(--text-muted)", letterSpacing: "0.08em", textTransform: "uppercase", whiteSpace: "nowrap" }}>
              Detect &bull; Locate &bull; Rescue &bull; Save Lives
            </div>
          </div>

          {/* Simulate Fire / Refresh (Dashboard tab only). Each is its own block with its name;
              side-by-side on very wide screens, stacked on smaller ones so the navbar never overflows */}
          {activeTab === "Dashboard" && (
            <div
              style={{
                display: "flex", flexDirection: xwide ? "row" : "column", alignItems: "stretch",
                gap: xwide ? 8 : 4, marginLeft: 6, paddingLeft: 14, borderLeft: "1px solid var(--border-subtle)",
              }}
            >
              <button
                disabled={simulating || !canOperate}
                title={canOperate ? "" : "Operator or admin access required"}
                onClick={() => window.dispatchEvent(new Event("resq:simulate"))}
                style={{
                  ...actionBtn,
                  padding: xwide ? "7px 14px" : "4px 12px",
                  background: "linear-gradient(180deg, #ff4b30, #e5251b)",
                  border: "1px solid #ff6a4d",
                  color: "#fff",
                  boxShadow: "0 0 12px rgba(255,59,48,0.5)",
                  opacity: simulating || !canOperate ? 0.5 : 1,
                  cursor: simulating || !canOperate ? "not-allowed" : "pointer",
                }}
              >
                <Flame size={13} strokeWidth={2.4} />
                {simulating ? "Simulating..." : "Simulate Fire"}
              </button>
              <button
                disabled={refreshing}
                onClick={() => window.dispatchEvent(new Event("resq:refresh"))}
                style={{
                  ...actionBtn,
                  padding: xwide ? "7px 14px" : "4px 12px",
                  background: "rgba(8,47,58,0.85)",
                  border: "1px solid rgba(34,211,238,0.45)",
                  color: "var(--cyan)",
                  opacity: refreshing ? 0.7 : 1,
                  cursor: refreshing ? "wait" : "pointer",
                }}
              >
                <style>{"@keyframes resq-spin{to{transform:rotate(360deg)}}"}</style>
                <RefreshCw size={13} strokeWidth={2.4} style={refreshing ? { animation: "resq-spin 0.8s linear infinite" } : undefined} />
                {refreshing ? "Refreshing..." : "Refresh"}
              </button>
            </div>
          )}
        </div>

        {/* CENTER: navigation tabs */}
        <nav style={{ display: "flex", gap: 4, justifySelf: "center" }}>
          {tabs.map((tab) => {
            const Icon = TAB_ICONS[tab];
            const active = activeTab === tab;
            return (
              <button
                key={tab}
                onClick={() => onTabChange(tab)}
                style={{
                  display: "flex", flexDirection: "column", alignItems: "center", gap: 4,
                  background: active ? "rgba(34,211,238,0.15)" : "transparent",
                  color: active ? "var(--cyan)" : "var(--text-muted)",
                  border: active ? "1px solid var(--border-subtle)" : "1px solid transparent",
                  borderRadius: 8,
                  padding: "7px 12px",
                  fontSize: 12.5,
                  fontWeight: 600,
                  cursor: "pointer",
                  whiteSpace: "nowrap",
                }}
              >
                {Icon && <Icon size={14} />}
                {tab}
              </button>
            );
          })}
        </nav>

        {/* RIGHT: tagline (wide screens only), time + date, system online, command center */}
        <div style={{ display: "flex", alignItems: "center", gap: 16, justifySelf: "end" }}>
          {wide && (
            <div style={{ textAlign: "right", fontSize: 9.5, lineHeight: 1.5, color: "var(--text-muted)", letterSpacing: "0.06em", whiteSpace: "nowrap" }}>
              SAFER BUILDINGS<br />SAFER COMMUNITIES<br />BRIGHTER TOMORROWS
            </div>
          )}
          <NotificationBell canOperate={canOperate} />
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: 13, color: "#fff", fontWeight: 700, fontVariantNumeric: "tabular-nums", whiteSpace: "nowrap" }}>
              {timeStr}
            </div>
            <div style={{ fontSize: 10, color: "var(--text-muted)", whiteSpace: "nowrap" }}>{dateStr}</div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11.5, fontWeight: 700, color: "var(--green)", whiteSpace: "nowrap" }}>
            <Wifi size={14} />
            <span className="pulse">SYSTEM ONLINE</span>
          </div>
          <div>
            <div className="pill pill-safe" style={{ whiteSpace: "nowrap" }}>COMMAND CENTER</div>
            <div style={{ fontSize: 9, color: "var(--text-muted)", textAlign: "center", marginTop: 3, whiteSpace: "nowrap" }}>
              {user ? (
                <>
                  {user.username}{user.username !== user.role ? ` · ${user.role}` : ""} ·{" "}
                  <button onClick={onLogout} style={{ background: "none", border: "none", padding: 0, color: "var(--cyan)", cursor: "pointer", fontSize: 9, textDecoration: "underline" }}>
                    Sign out
                  </button>
                </>
              ) : "Fire & Emergency Response"}
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}

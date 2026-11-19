import React from "react";
import { Loader2, AlertTriangle } from "lucide-react";
import { lastApiError } from "../api/client.js";

export function Loading({ label = "Loading data from RESQ AI backend..." }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, padding: 24, color: "var(--text-muted)" }}>
      <Loader2 size={18} className="pulse" />
      <span style={{ fontSize: 13.5 }}>{label}</span>
    </div>
  );
}

export function ErrorState({ message, onRetry }) {
  const text = message || lastApiError.message || "Could not reach the RESQ AI backend API.";
  const title = !message && lastApiError.kind === "server" ? "Server error" : "Connection error";
  return (
    <div
      className="glass-panel"
      style={{ padding: 20, display: "flex", alignItems: "center", gap: 12, borderColor: "rgba(239,68,68,0.4)" }}
    >
      <AlertTriangle size={20} color="var(--red)" />
      <div style={{ flex: 1 }}>
        <div style={{ fontWeight: 700, fontSize: 13.5 }}>{title}</div>
        <div style={{ fontSize: 12.5, color: "var(--text-muted)" }}>{text}</div>
      </div>
      {onRetry && (
        <button className="btn" onClick={onRetry}>Retry</button>
      )}
    </div>
  );
}

export function RiskPill({ level }) {
  const map = {
    Critical: "pill-critical",
    "High Risk": "pill-high",
    Moderate: "pill-moderate",
    Safe: "pill-safe",
  };
  return <span className={`pill ${map[level] || "pill-moderate"}`}>{level}</span>;
}

export function SectionTitle({ children, right }) {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
      <h3 style={{ margin: 0, fontSize: 14, letterSpacing: "0.03em", color: "#fff", textTransform: "uppercase" }}>
        {children}
      </h3>
      {right}
    </div>
  );
}

// Number formatting that never crashes on a missing sensor value (null/undefined -> "N/A").
export const fmtNum = (v, digits = 0, unit = "") => (v === null || v === undefined || Number.isNaN(v) ? "N/A" : `${Number(v).toFixed(digits)}${unit}`);

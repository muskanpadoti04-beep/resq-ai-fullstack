import React, { useEffect } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";

/** Header used by the bottom dashboard panels: icon + title on the left, "View Details ›" on the right. */
export function PanelHeader({ icon: Icon, title, actionLabel = "View Details", onAction }) {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8, marginBottom: 14 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
        {Icon && <Icon size={16} strokeWidth={2.2} color="var(--rq-cyan)" style={{ flexShrink: 0 }} />}
        <h3
          style={{
            margin: 0, fontSize: 15.5, fontWeight: 700, color: "var(--rq-white)",
            letterSpacing: "0.01em", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
          }}
        >
          {title}
        </h3>
      </div>
      {onAction && (
        <button
          className="btn"
          onClick={onAction}
          style={{
            padding: "4px 10px", fontSize: 11.5, whiteSpace: "nowrap", flexShrink: 0,
            borderColor: "rgba(32,200,255,0.55)", color: "var(--rq-cyan)", background: "rgba(32,200,255,0.06)",
          }}
        >
          {actionLabel} ›
        </button>
      )}
    </div>
  );
}

/**
 * Centered pop-up with the full data behind a panel.
 * Rendered in a portal on purpose: .glass-panel uses backdrop-filter, which would
 * otherwise trap a position:fixed child inside the panel.
 */
export function DetailDrawer({ open, title, icon: Icon, onClose, children }) {
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return createPortal(
    <div
      className="rq-tech"
      style={{ position: "fixed", inset: 0, zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center", padding: 16 }}
    >
      <div onClick={onClose} style={{ position: "absolute", inset: 0, background: "rgba(2,6,14,0.6)" }} />
      <aside
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="fade-in"
        style={{
          position: "relative", width: "min(680px, 100%)", maxHeight: "86vh", overflowY: "auto",
          background: "var(--bg-panel)", border: "1px solid rgba(32,200,255,0.4)", borderRadius: 14,
          boxShadow: "0 0 40px rgba(32,200,255,0.15), 0 16px 48px rgba(0,0,0,0.6)", padding: 22,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 18 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            {Icon && <Icon size={18} strokeWidth={2.2} color="var(--rq-cyan)" />}
            <h2 style={{ margin: 0, fontSize: 19, fontWeight: 700, color: "var(--rq-white)" }}>{title}</h2>
          </div>
          <button className="btn" onClick={onClose} aria-label="Close" style={{ padding: "5px 8px", display: "flex" }}>
            <X size={15} />
          </button>
        </div>
        {children}
      </aside>
    </div>,
    document.body
  );
}

/** One bordered row inside a drawer. */
export function DrawerRow({ children, accent }) {
  return (
    <div
      style={{
        padding: "10px 12px", borderRadius: 10, marginBottom: 8,
        border: `1px solid ${accent || "var(--border-subtle)"}`,
        background: "rgba(14,29,51,0.7)", fontSize: 13,
      }}
    >
      {children}
    </div>
  );
}

export const muted = { color: "rgba(234,244,255,0.62)", fontSize: 12 };

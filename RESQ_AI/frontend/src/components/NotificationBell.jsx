import React, { useEffect, useState, useCallback } from "react";
import { Bell } from "lucide-react";
import { getNotifications, markNotificationsRead } from "../api/client.js";

const COLORS = { critical: "#ff3b30", warning: "#ffb020", info: "#20c8ff" };

export default function NotificationBell({ canOperate }) {
  const [data, setData] = useState({ unread: 0, items: [] });
  const [open, setOpen] = useState(false);

  const load = useCallback(() => {
    getNotifications().then(setData).catch(() => {});
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 8000);
    window.addEventListener("resq:refresh", load);
    return () => { clearInterval(t); window.removeEventListener("resq:refresh", load); };
  }, [load]);

  const readAll = async () => { try { await markNotificationsRead(); } catch { /* ignore */ } load(); };

  return (
    <div style={{ position: "relative" }}>
      <button onClick={() => setOpen((o) => !o)} aria-label="Notifications" title="Notifications"
        style={{ position: "relative", background: "transparent", border: "1px solid var(--border-subtle)", borderRadius: 8,
                 color: data.unread ? "#ffb020" : "var(--text-muted)", padding: "6px 8px", cursor: "pointer", display: "flex" }}>
        <Bell size={16} />
        {data.unread > 0 && (
          <span style={{ position: "absolute", top: -6, right: -6, minWidth: 16, height: 16, borderRadius: 8, background: "#ff3b30",
                         color: "#fff", fontSize: 10, fontWeight: 800, display: "grid", placeItems: "center", padding: "0 3px" }}>
            {data.unread > 99 ? "99+" : data.unread}
          </span>
        )}
      </button>
      {open && (
        <div className="glass-panel" style={{ position: "absolute", right: 0, top: 38, width: 340, maxHeight: 380, overflowY: "auto",
                                              padding: 12, zIndex: 50, background: "#0b1626" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <strong style={{ fontSize: 13 }}>Notifications</strong>
            {canOperate && data.unread > 0 && (
              <button onClick={readAll} style={{ fontSize: 11, background: "none", border: "none", color: "var(--cyan)", cursor: "pointer" }}>Mark all read</button>
            )}
          </div>
          {data.items.length === 0 && <div style={{ fontSize: 12, color: "var(--text-muted)" }}>No notifications.</div>}
          {data.items.map((n) => (
            <div key={n.id} style={{ borderLeft: `3px solid ${COLORS[n.level] || COLORS.info}`, padding: "5px 8px", marginBottom: 6,
                                     background: n.read ? "transparent" : "rgba(255,255,255,0.04)" }}>
              <div style={{ fontSize: 12, lineHeight: 1.35 }}>{n.message}</div>
              <div style={{ fontSize: 10.5, color: "var(--text-muted)", marginTop: 2 }}>
                {n.kind === "escalation" ? `Escalation level ${n.escalation_level} · ` : ""}{new Date(n.time + "Z").toLocaleTimeString()}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

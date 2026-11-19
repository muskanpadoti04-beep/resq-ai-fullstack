import React, { useEffect } from "react";
import { CheckCircle2, XCircle } from "lucide-react";

export default function Toast({ type = "success", message, onDone }) {
  useEffect(() => {
    const t = setTimeout(onDone, 3200);
    return () => clearTimeout(t);
  }, [onDone]);

  const isSuccess = type === "success";

  return (
    <div
      className="glass-panel fade-in"
      style={{
        position: "fixed",
        bottom: 24,
        right: 24,
        padding: "12px 16px",
        display: "flex",
        alignItems: "center",
        gap: 10,
        borderColor: isSuccess ? "rgba(34,197,94,0.4)" : "rgba(239,68,68,0.4)",
        boxShadow: isSuccess ? "0 0 20px var(--green-glow)" : "0 0 20px var(--red-glow)",
        zIndex: 100,
        maxWidth: 360,
      }}
    >
      {isSuccess ? <CheckCircle2 size={18} color="var(--green)" /> : <XCircle size={18} color="var(--red)" />}
      <span style={{ fontSize: 13.5 }}>{message}</span>
    </div>
  );
}

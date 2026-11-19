import React, { useState } from "react";
import { ShieldAlert, LogIn } from "lucide-react";
import { login, setToken, errorMessage } from "../api/client.js";

const DEMO = [
  ["admin", "admin123", "everything, incl. reset and audit log"],
  ["operator", "operator123", "run incidents and rescue teams"],
  ["viewer", "viewer123", "read-only"],
];

export default function LoginPage({ onLoggedIn }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const res = await login(username.trim(), password);
      setToken(res.access_token);
      onLoggedIn({ username: res.username, role: res.role });
    } catch (err) {
      setError(errorMessage(err, "Could not sign in."));
    } finally {
      setBusy(false);
    }
  };

  const input = {
    width: "100%", padding: "10px 12px", borderRadius: 8, fontSize: 14,
    background: "rgba(6,12,23,0.7)", border: "1px solid var(--border-subtle)", color: "#fff", outline: "none",
  };

  return (
    <div style={{ minHeight: "100vh", display: "grid", placeItems: "center", padding: 20 }}>
      <form onSubmit={submit} className="glass-panel fade-in" style={{ width: "100%", maxWidth: 380, padding: 28 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
          <ShieldAlert size={28} color="var(--red)" />
          <div style={{ fontSize: 22, fontWeight: 800, letterSpacing: "0.04em", color: "#fff" }}>
            RESQ <span style={{ color: "var(--red)" }}>AI</span>
          </div>
        </div>
        <div style={{ fontSize: 12.5, color: "var(--text-muted)", marginBottom: 20 }}>Sign in to the command center</div>

        <label style={{ fontSize: 11.5, color: "var(--text-muted)" }}>Username</label>
        <input style={{ ...input, marginBottom: 12 }} value={username} autoFocus autoComplete="username"
               onChange={(e) => setUsername(e.target.value)} />
        <label style={{ fontSize: 11.5, color: "var(--text-muted)" }}>Password</label>
        <input style={{ ...input, marginBottom: 14 }} type="password" value={password} autoComplete="current-password"
               onChange={(e) => setPassword(e.target.value)} />

        {error && <div style={{ color: "var(--red)", fontSize: 12.5, marginBottom: 12 }}>{error}</div>}

        <button className="btn" type="submit" disabled={busy || !username || !password}
                style={{ width: "100%", display: "flex", justifyContent: "center", alignItems: "center", gap: 6, padding: "10px 0" }}>
          <LogIn size={15} /> {busy ? "Signing in..." : "Sign in"}
        </button>

        <div style={{ marginTop: 20, paddingTop: 14, borderTop: "1px solid var(--border-subtle)", fontSize: 11.5, color: "var(--text-muted)", lineHeight: 1.7 }}>
          <div style={{ fontWeight: 700, marginBottom: 4 }}>Demo accounts</div>
          {DEMO.map(([u, p, what]) => (
            <div key={u}>
              <button type="button" onClick={() => { setUsername(u); setPassword(p); }}
                      style={{ background: "none", border: "none", padding: 0, color: "var(--cyan)", cursor: "pointer", fontSize: 11.5 }}>
                {u} / {p}
              </button>{" "}
              <span>— {what}</span>
            </div>
          ))}
        </div>
      </form>
    </div>
  );
}

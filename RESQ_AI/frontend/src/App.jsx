import React, { useState, useEffect, useCallback } from "react";
import Navbar from "./components/Navbar.jsx";
import Toast from "./components/Toast.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import BuildingPage from "./pages/BuildingPage.jsx";
import OccupantsPage from "./pages/OccupantsPage.jsx";
import RescueTeamsPage from "./pages/RescueTeamsPage.jsx";
import MedicalPage from "./pages/MedicalPage.jsx";
import AnalyticsPage from "./pages/AnalyticsPage.jsx";
import ReportsPage from "./pages/ReportsPage.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import { AuthProvider } from "./components/AuthContext.jsx";
import { ErrorState, Loading } from "./components/Common.jsx";
import { getMe, setToken, getLiveVersion } from "./api/client.js";

const TABS = ["Dashboard", "Building", "Occupants", "Rescue Teams", "Medical", "Analytics", "Reports"];

export default function App() {
  const [activeTab, setActiveTab] = useState("Dashboard");
  const [toast, setToast] = useState(null); // { type: 'success'|'error', message }
  // auth: "checking" | "login" | "error" | { username, role }
  const [auth, setAuth] = useState("checking");

  const checkSession = useCallback(async () => {
    setAuth("checking");
    try {
      const me = await getMe();
      setAuth({ username: me.username, role: me.role });
    } catch (e) {
      setAuth(e?.response?.status === 401 ? "login" : "error");
    }
  }, []);

  useEffect(() => { checkSession(); }, [checkSession]);

  useEffect(() => {
    const onUnauthorized = () => { setToken(""); setAuth("login"); };
    window.addEventListener("resq:unauthorized", onUnauthorized);
    return () => window.removeEventListener("resq:unauthorized", onUnauthorized);
  }, []);

  // Live updates: poll a tiny change counter; reload dashboard data only when something changed.
  const signedIn = auth && typeof auth === "object";
  useEffect(() => {
    if (!signedIn) return undefined;
    let last = null;
    const tick = async () => {
      if (document.hidden) return;
      try {
        const v = await getLiveVersion();
        if (last !== null && v !== last) window.dispatchEvent(new Event("resq:refresh"));
        last = v;
      } catch { /* backend briefly unreachable: try again next tick */ }
    };
    tick();
    const t = setInterval(tick, 5000);
    return () => clearInterval(t);
  }, [signedIn]);

  const logout = () => { setToken(""); setActiveTab("Dashboard"); setAuth("login"); };

  const showToast = (type, message) => {
    setToast({ type, message, key: Date.now() });
  };

  const renderPage = () => {
    switch (activeTab) {
      case "Dashboard":
        return <Dashboard showToast={showToast} onNavigate={setActiveTab} />;
      case "Building":
        return <BuildingPage showToast={showToast} />;
      case "Occupants":
        return <OccupantsPage />;
      case "Rescue Teams":
        return <RescueTeamsPage showToast={showToast} />;
      case "Medical":
        return <MedicalPage />;
      case "Analytics":
        return <AnalyticsPage />;
      case "Reports":
        return <ReportsPage />;
      default:
        return <Dashboard showToast={showToast} onNavigate={setActiveTab} />;
    }
  };

  if (auth === "checking") return <div style={{ padding: 40 }}><Loading label="Connecting to RESQ AI..." /></div>;
  if (auth === "error") return <div style={{ padding: 40 }}><ErrorState onRetry={checkSession} /></div>;
  if (auth === "login") return <LoginPage onLoggedIn={setAuth} />;

  return (
    <AuthProvider value={auth}>
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <Navbar tabs={TABS} activeTab={activeTab} onTabChange={setActiveTab} user={auth} onLogout={logout} />
      <main style={{ flex: 1, padding: "20px 24px", maxWidth: 1600, margin: "0 auto", width: "100%" }}>
        {renderPage()}
      </main>
      {toast && <Toast key={toast.key} type={toast.type} message={toast.message} onDone={() => setToast(null)} />}
    </div>
    </AuthProvider>
  );
}

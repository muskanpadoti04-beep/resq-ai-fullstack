import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
});

export default api;

// ---- login token (kept in the browser so a refresh does not sign you out) -----
const TOKEN_KEY = "resq_token";
export const getToken = () => { try { return localStorage.getItem(TOKEN_KEY) || ""; } catch { return ""; } };
export const setToken = (token) => {
  try { token ? localStorage.setItem(TOKEN_KEY, token) : localStorage.removeItem(TOKEN_KEY); } catch { /* storage blocked */ }
};
api.interceptors.request.use((cfg) => {
  const token = getToken();
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});

// ---- readable API errors -------------------------------------------------
// Backend errors look like {"detail": "...", "code": "..."}; a missing response means
// the backend is unreachable. The last error is kept so ErrorState can show it.
export const lastApiError = { message: "", kind: "network" };

export function errorMessage(err, fallback = "Something went wrong.") {
  if (err?.apiMessage) return err.apiMessage;
  return err?.response?.data?.detail && typeof err.response.data.detail === "string"
    ? err.response.data.detail
    : fallback;
}

api.interceptors.response.use(
  (res) => res,
  (err) => {
    let message;
    let kind = "server";
    if (err.code === "ECONNABORTED") {
      kind = "network";
      message = "The backend took too long to respond. Check that it is running and try again.";
    } else if (!err.response) {
      kind = "network";
      message = `Cannot reach the backend at ${API_BASE_URL}. Make sure uvicorn is running.`;
    } else {
      const d = err.response.data?.detail;
      message = typeof d === "string" ? d
        : Array.isArray(d) ? d.map((x) => x.msg).join("; ")
        : `Server error (${err.response.status}).`;
    }
    if (err.response?.status === 401 && !String(err.config?.url || "").includes("/api/auth/login")) {
      window.dispatchEvent(new Event("resq:unauthorized"));
    }
    err.apiMessage = message;
    lastApiError.message = message;
    lastApiError.kind = kind;
    return Promise.reject(err);
  }
);

export const getDashboardSummary = () => api.get("/api/dashboard/summary").then((r) => r.data);
export const getFloors = () => api.get("/api/floors").then((r) => r.data);
export const getRooms = () => api.get("/api/rooms").then((r) => r.data);
export const getOccupants = () => api.get("/api/occupants").then((r) => r.data);
export const getIncidents = () => api.get("/api/incidents").then((r) => r.data);
export const getActiveIncidents = () => api.get("/api/incidents/active").then((r) => r.data);
export const acknowledgeIncident = (id) => api.post(`/api/incidents/${id}/acknowledge`).then((r) => r.data);
export const getRescueTeams = () => api.get("/api/rescue-teams").then((r) => r.data);
export const dispatchTeam = (teamId, incidentId) =>
  api.post(`/api/rescue-teams/${teamId}/dispatch`, null, { params: incidentId ? { incident_id: incidentId } : {} }).then((r) => r.data);
export const arriveTeam = (teamId) => api.post(`/api/rescue-teams/${teamId}/arrive`).then((r) => r.data);
export const resolveIncident = (id) => api.post(`/api/incidents/${id}/resolve`).then((r) => r.data);
export const login = (username, password) => api.post("/api/auth/login", { username, password }).then((r) => r.data);
export const getMe = () => api.get("/api/auth/me").then((r) => r.data);
export const getAuditLogs = (limit = 50) => api.get("/api/audit-logs", { params: { limit } }).then((r) => r.data);
export const getRescueRoute = (roomId) => api.get(`/api/routes/rescue/${roomId}`).then((r) => r.data);
export const completeRescue = (teamId) => api.post(`/api/rescue-teams/${teamId}/complete-rescue`).then((r) => r.data);
export const navigateTeam = (teamId) => api.post(`/api/rescue-teams/${teamId}/navigate`).then((r) => r.data);
export const getMedicalSupport = () => api.get("/api/medical-support").then((r) => r.data);
export const getTimeline = () => api.get("/api/timeline").then((r) => r.data);
export const getAnalyticsOccupants = () => api.get("/api/analytics/occupants").then((r) => r.data);
export const getAnalyticsIncidents = () => api.get("/api/analytics/incidents").then((r) => r.data);
export const getAnalyticsRisk = () => api.get("/api/analytics/risk").then((r) => r.data);
export const getMlForecast = () => api.get("/api/ml/forecast").then((r) => r.data);
export const getMlModelInfo = () => api.get("/api/ml/model-info").then((r) => r.data);
export const getLiveVersion = () => api.get("/api/live/version").then((r) => r.data.version);
export const getNotifications = () => api.get("/api/notifications").then((r) => r.data);
export const markNotificationsRead = () => api.post("/api/notifications/read").then((r) => r.data);
export const resetDemo = () => api.post("/api/simulation/reset").then((r) => r.data);
export const simulateFire = () => api.post("/api/simulation/fire").then((r) => r.data);
export const getAnalyticsSummary = () => api.get("/api/analytics/summary").then((r) => r.data);
export const getSensorHistory = (roomId, minutes = 30) =>
  api.get("/api/analytics/sensor-history", { params: { room_id: roomId || undefined, minutes } }).then((r) => r.data);
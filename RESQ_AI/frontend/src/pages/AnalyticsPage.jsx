import React, { useCallback, useEffect, useState } from "react";
import {
  BarChart, Bar, Cell, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, ReferenceLine,
} from "recharts";
import { Loading, ErrorState, SectionTitle } from "../components/Common.jsx";
import { getAnalyticsSummary, getSensorHistory } from "../api/client.js";

const TOOLTIP_STYLE = { background: "#0e1d33", border: "1px solid var(--border-subtle)", borderRadius: 8, fontSize: 12 };
const GRID_STYLE = { stroke: "rgba(255,255,255,0.06)" };
const AXIS_STYLE = { fontSize: 11.5, fill: "#9fb4c8" };
const RISK_COLOUR = { Safe: "#30d158", Moderate: "#ffd60a", "High Risk": "#ff9f0a", Critical: "#ff3b30" };
const SEV_COLOUR = { Critical: "#ff3b30", High: "#ff9f0a", Moderate: "#ffd60a", Low: "#30d158" };
const PEOPLE_COLOUR = { Safe: "#30d158", "High Risk": "#ff9f0a", Critical: "#ff3b30", Rescued: "#3b9cff" };

const mins = (v) => (v === null || v === undefined ? "–" : `${v} min`);
const clock = (iso, withSeconds) =>
  new Date(iso).toLocaleTimeString([], withSeconds ? { hour: "2-digit", minute: "2-digit", second: "2-digit" } : { hour: "2-digit", minute: "2-digit" });

function Kpi({ label, value, sub, colour }) {
  return (
    <div className="glass-panel" style={{ padding: "14px 16px" }}>
      <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: 0.6, color: "#9fb4c8", textTransform: "uppercase" }}>{label}</div>
      <div style={{ fontSize: 30, fontWeight: 800, marginTop: 6, color: colour || "#fff", lineHeight: 1.1 }}>{value}</div>
      {sub && <div style={{ fontSize: 12.5, color: "#9fb4c8", marginTop: 6 }}>{sub}</div>}
    </div>
  );
}

function ChartCard({ title, note, children, wide, height = 230 }) {
  return (
    <div className="glass-panel" style={{ padding: 18, gridColumn: wide ? "1 / -1" : undefined }}>
      <SectionTitle>{title}</SectionTitle>
      {note && <div style={{ fontSize: 12.5, color: "#9fb4c8", margin: "-4px 0 10px" }}>{note}</div>}
      <div style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">{children}</ResponsiveContainer>
      </div>
    </div>
  );
}

function Empty({ title, note, text }) {
  return (
    <div className="glass-panel" style={{ padding: 18 }}>
      <SectionTitle>{title}</SectionTitle>
      {note && <div style={{ fontSize: 12.5, color: "#9fb4c8", margin: "-4px 0 10px" }}>{note}</div>}
      <div style={{ height: 200, display: "flex", alignItems: "center", justifyContent: "center", textAlign: "center", color: "#9fb4c8", fontSize: 14, padding: 20 }}>{text}</div>
    </div>
  );
}

// Presentational part: only draws what it is given (easy to test, no data loading here)
export function AnalyticsView({ summary, history, onRoomChange }) {
  const k = summary.kpis;
  const breakdown = summary.response_breakdown || [];
  const hasResponse = breakdown.some((b) => b.assign_min || b.travel_min || b.rescue_min);
  const timeline = (summary.timeline || []).map((t) => ({ hour: clock(t.hour), Opened: t.opened, Resolved: t.resolved }));
  const hasTimeline = timeline.some((t) => t.Opened || t.Resolved);
  const points = ((history && history.points) || []).map((p) => ({ time: clock(p.t, true), Temperature: p.temperature, Smoke: p.smoke_level }));
  const peopleTotal = (summary.people || []).reduce((a, p) => a + p.count, 0);

  return (
    <div className="fade-in" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: 14 }}>
        <Kpi label="Active incidents" value={k.active_incidents} colour={k.active_incidents > 0 ? "#ff5a4f" : "#30d158"} sub={`${k.resolved_incidents} resolved so far`} />
        <Kpi label="Team assigned in" value={mins(k.avg_assign_min)} sub="average, from detection" />
        <Kpi label="Rescue completed in" value={mins(k.avg_total_min)} sub="average, from detection" />
        <Kpi label="People at risk now" value={k.people_at_risk} colour={k.people_at_risk > 0 ? "#ff9f0a" : "#30d158"} sub={`${k.people_trapped} trapped · ${k.people_inside} inside`} />
        <Kpi label="People rescued" value={k.people_rescued} colour="#3b9cff" sub={`${k.humans_rescued} people · ${k.animals_rescued} animals`} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(420px, 1fr))", gap: 16 }}>
        <ChartCard title="Rooms by risk level, per floor" note="Each bar is one floor. Orange and red parts are rooms in danger.">
          <BarChart data={summary.by_floor} margin={{ left: -10 }}>
            <CartesianGrid {...GRID_STYLE} vertical={false} />
            <XAxis dataKey="label" tick={AXIS_STYLE} />
            <YAxis tick={AXIS_STYLE} allowDecimals={false} />
            <Tooltip contentStyle={TOOLTIP_STYLE} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            {["Safe", "Moderate", "High Risk", "Critical"].map((lvl) => (
              <Bar key={lvl} dataKey={lvl} stackId="rooms" fill={RISK_COLOUR[lvl]} />
            ))}
          </BarChart>
        </ChartCard>

        {peopleTotal === 0 ? (
          <Empty title="People status" note="People still inside, and people already rescued." text="No occupant data yet." />
        ) : (
          <ChartCard title="People status" note="People still inside the building by risk, and people already rescued.">
            <BarChart data={summary.people} margin={{ left: -10 }}>
              <CartesianGrid {...GRID_STYLE} vertical={false} />
              <XAxis dataKey="status" tick={AXIS_STYLE} />
              <YAxis tick={AXIS_STYLE} allowDecimals={false} />
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {summary.people.map((p) => <Cell key={p.status} fill={PEOPLE_COLOUR[p.status]} />)}
              </Bar>
            </BarChart>
          </ChartCard>
        )}

        {hasResponse ? (
          <ChartCard title="Response time per incident (minutes)" note="Detection to team assigned, team travel, and rescue on scene. Last 8 incidents.">
            <BarChart data={breakdown} margin={{ left: -10 }}>
              <CartesianGrid {...GRID_STYLE} vertical={false} />
              <XAxis dataKey="room_id" tick={AXIS_STYLE} />
              <YAxis tick={AXIS_STYLE} />
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="assign_min" name="Team assigned" stackId="t" fill="#ffd60a" />
              <Bar dataKey="travel_min" name="Team travel" stackId="t" fill="#3b9cff" />
              <Bar dataKey="rescue_min" name="Rescue" stackId="t" fill="#30d158" />
            </BarChart>
          </ChartCard>
        ) : (
          <Empty title="Response time per incident (minutes)" note="Detection to team assigned, team travel, and rescue on scene."
            text="No incident has been dispatched yet. Start the sensor simulator and the response times will appear here." />
        )}

        {hasTimeline ? (
          <ChartCard title="Incidents per hour" note="Opened and resolved, last 12 hours.">
            <BarChart data={timeline} margin={{ left: -10 }}>
              <CartesianGrid {...GRID_STYLE} vertical={false} />
              <XAxis dataKey="hour" tick={AXIS_STYLE} />
              <YAxis tick={AXIS_STYLE} allowDecimals={false} />
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="Opened" fill="#ff5a4f" radius={[4, 4, 0, 0]} />
              <Bar dataKey="Resolved" fill="#30d158" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ChartCard>
        ) : (
          <Empty title="Incidents per hour" note="Opened and resolved, last 12 hours." text="No incidents in the last 12 hours." />
        )}

        <ChartCard title="Active incidents by floor" note="Where the open incidents are right now.">
          <BarChart data={summary.by_floor} margin={{ left: -10 }}>
            <CartesianGrid {...GRID_STYLE} vertical={false} />
            <XAxis dataKey="label" tick={AXIS_STYLE} />
            <YAxis tick={AXIS_STYLE} allowDecimals={false} />
            <Tooltip contentStyle={TOOLTIP_STYLE} />
            <Bar dataKey="active_incidents" name="Active incidents" fill="#22d3ee" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ChartCard>

        <ChartCard title="Incidents by severity" note="All incidents so far, from Critical to Low.">
          <BarChart data={summary.severity} margin={{ left: -10 }}>
            <CartesianGrid {...GRID_STYLE} vertical={false} />
            <XAxis dataKey="severity" tick={AXIS_STYLE} />
            <YAxis tick={AXIS_STYLE} allowDecimals={false} />
            <Tooltip contentStyle={TOOLTIP_STYLE} />
            <Bar dataKey="count" radius={[4, 4, 0, 0]}>
              {summary.severity.map((s) => <Cell key={s.severity} fill={SEV_COLOUR[s.severity]} />)}
            </Bar>
          </BarChart>
        </ChartCard>

        {points.length < 2 ? (
          <div style={{ gridColumn: "1 / -1" }}>
            <Empty title={`Live sensors${history && history.room_id ? ` · room ${history.room_id}` : ""}`}
              note="Temperature and smoke of one room, last 30 minutes."
              text="No recent readings for this room. Start the sensor simulator to see the live trend." />
          </div>
        ) : (
          <ChartCard wide height={260} title={`Live sensors · room ${history.room_id}`} note="Temperature (left axis) and smoke (right axis), last 30 minutes. Dashed lines are the danger levels used by the risk engine.">
            <LineChart data={points} margin={{ right: 10 }}>
              <CartesianGrid {...GRID_STYLE} vertical={false} />
              <XAxis dataKey="time" tick={AXIS_STYLE} minTickGap={40} />
              <YAxis yAxisId="t" tick={AXIS_STYLE} unit="°" />
              <YAxis yAxisId="s" orientation="right" tick={AXIS_STYLE} unit="%" domain={[0, 100]} />
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <ReferenceLine yAxisId="t" y={80} stroke="#ff9f0a" strokeDasharray="5 4" />
              <ReferenceLine yAxisId="s" y={70} stroke="#64d2ff" strokeDasharray="5 4" />
              <Line yAxisId="t" type="monotone" dataKey="Temperature" stroke="#ff9f0a" strokeWidth={2.4} dot={false} isAnimationActive={false} />
              <Line yAxisId="s" type="monotone" dataKey="Smoke" stroke="#64d2ff" strokeWidth={2.4} dot={false} isAnimationActive={false} />
            </LineChart>
          </ChartCard>
        )}
      </div>

      {history && history.rooms && history.rooms.length > 0 && (
        <div style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 13.5 }}>
          <label htmlFor="room-pick" style={{ color: "#9fb4c8" }}>Show live sensors for room:</label>
          <select id="room-pick" value={history.room_id || ""} onChange={(e) => onRoomChange(e.target.value)}
            style={{ background: "#0e1d33", color: "#fff", border: "1px solid rgba(255,255,255,0.2)", borderRadius: 8, padding: "6px 10px", fontSize: 13.5 }}>
            {history.rooms.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        </div>
      )}
    </div>
  );
}

export default function AnalyticsPage() {
  const [summary, setSummary] = useState(null);
  const [history, setHistory] = useState(null);
  const [room, setRoom] = useState(null);      // null = let the backend pick the room with the worst incident
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const load = useCallback(async (silent) => {
    try {
      const [s, h] = await Promise.all([getAnalyticsSummary(), getSensorHistory(room, 30)]);
      setSummary(s);
      setHistory(h);
      setError(false);
    } catch {
      if (!silent) setError(true);             // a failed background refresh keeps showing the last data
    } finally {
      setLoading(false);
    }
  }, [room]);

  useEffect(() => { load(false); }, [load]);
  useEffect(() => {
    const id = setInterval(() => load(true), 5000);
    return () => clearInterval(id);
  }, [load]);

  if (loading) return <Loading />;
  if (error || !summary) return <ErrorState onRetry={() => load(false)} />;
  return <AnalyticsView summary={summary} history={history} onRoomChange={setRoom} />;
}
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Bar as BarChart, Line } from "react-chartjs-2";
import { Chart, BarElement, CategoryScale, LinearScale, LineElement, PointElement, Tooltip, Legend, Filler } from "chart.js";
import { api, download, money, thisMonth } from "../api";
import { Avatar, Bar, Num, Ring } from "../components.jsx";
import Wheel from "../Wheel.jsx";
Chart.register(BarElement, CategoryScale, LinearScale, LineElement, PointElement, Tooltip, Legend, Filler);
const rise = (i) => ({ initial: { opacity: 0, y: 24 }, animate: { opacity: 1, y: 0 }, transition: { delay: i * 0.08, duration: 0.5 } });

export default function Dashboard({ openWrapped }) {
  const [month, setMonth] = useState(thisMonth());
  const [d, setD] = useState(null);
  const [h, setH] = useState(null);
  const [story, setStory] = useState(null);
  const [notes, setNotes] = useState([]);
  const [err, setErr] = useState("");
  useEffect(() => { api(`/dashboard?month=${month}`).then(setD).catch((e) => setErr(e.message)); }, [month]);
  useEffect(() => { api("/health-score").then(setH); api("/story").then(setStory); api("/notifications").then(setNotes); }, []);
  if (err) return <div className="err">{err}</div>;
  if (!d) return <p className="muted">Loading…</p>;
  const totalBudget = d.budgets.reduce((s, b) => s + b.limit, 0);
  const budgetPct = totalBudget ? (d.expense / totalBudget) * 100 : d.income ? (d.expense / d.income) * 100 : 0;
  const saveRate = d.income ? Math.max(0, (d.savings / d.income) * 100) : 0;
  const tone = (p) => (p >= 100 ? "var(--coral)" : p >= 80 ? "var(--amber)" : "var(--teal)");
  const sc = h ? (h.score >= 70 ? "var(--green)" : h.score >= 45 ? "var(--amber)" : "var(--coral)") : "var(--teal)";
  const grid = { color: "rgba(150,165,190,.18)" }, tick = { color: "#97a4bb" };
  return (
    <>
      <div className="head">
        <h1>Hi, here's your money this month</h1>
        <div className="row" style={{ flex: "0 0 auto" }}>
          <label>Month<input type="month" value={month} onChange={(e) => e.target.value && setMonth(e.target.value)} /></label>
          <button className="btn" onClick={() => openWrapped()}>✨ Monthly Wrapped</button>
          <button className="btn ghost" onClick={() => download(`/reports/monthly?month=${month}&format=pdf`, `report-${month}.pdf`)}>PDF</button>
          <button className="btn ghost" onClick={() => download(`/reports/monthly?month=${month}&format=xlsx`, `report-${month}.xlsx`)}>Excel</button>
        </div>
      </div>
      <div className="notes" aria-live="polite">{notes.map((n, i) => <motion.div key={i} className={`note ${n.level}`} {...rise(i)}><span className="ic">{n.icon}</span><span>{n.text}</span></motion.div>)}</div>
      <div className="top3">
        <motion.div className="card stat" {...rise(0)}>
          <Ring pct={saveRate} color="var(--green)"><strong>{saveRate.toFixed(0)}%</strong><div className="muted small">kept</div></Ring>
          <div><div className="lbl">💰 Income</div><div className="n"><Num value={d.income} /> <small>{d.currency}</small></div><div className="muted small">Saved so far: {money(Math.max(0, d.savings), d.currency)}</div></div>
        </motion.div>
        <motion.div className="card stat" {...rise(1)}>
          <Ring pct={budgetPct} color={tone(budgetPct)}><strong>{budgetPct.toFixed(0)}%</strong><div className="muted small">used</div></Ring>
          <div><div className="lbl">🔥 Expenses</div><div className="n"><Num value={d.expense} /> <small>{d.currency}</small></div><div className="muted small">{totalBudget ? "of your total budgets" : "of your income"}</div></div>
        </motion.div>
        <motion.div className="card stat" {...rise(2)}>
          <Ring pct={h?.score ?? 0} color={sc}><strong style={{ fontSize: "1.5rem" }}><Num value={h?.score ?? 0} /></strong><div className="muted small">/100</div></Ring>
          <div style={{ flex: 1 }}><div className="lbl">Financial Health</div>
            {h && <><div className="n" style={{ fontSize: "1.2rem" }}><Avatar avatar={h.avatar} size="1.5rem" /> {h.level}</div>
              <div className="score-parts">{h.parts.map((p) => <div key={p.label}>{p.label} {p.value}<Bar pct={p.value} level={p.value < 50 ? "exceeded" : p.value < 75 ? "warning" : ""} /></div>)}</div></>}</div>
        </motion.div>
      </div>
      <div className="grid g2">
        <motion.div className="card" {...rise(3)} style={{ gridColumn: "1 / -1" }}><h2>Spending wheel · tap a slice</h2><Wheel data={d.by_category} prev={d.prev_by_category} currency={d.currency} /></motion.div>
        <motion.div className="card story" {...rise(4)}><h2>📈 Your Money Story</h2>
          {story?.lines.map((l, i) => <motion.p key={i} initial={{ opacity: 0, x: -16 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.4 + i * 0.35 }}>{l}</motion.p>)}
          <button className="btn ghost sm" onClick={() => openWrapped(story?.month)}>Watch it as a story</button></motion.div>
        <motion.div className="card" {...rise(5)}><h2>Budget use</h2>
          {d.budgets.length ? d.budgets.map((b) => <div className="meter" key={b.id}><div className="top"><span>{b.category}</span><span className="muted">{money(b.spent)} / {money(b.limit)}</span></div><Bar pct={b.pct} level={b.level} /></div>)
            : <p className="muted">No budgets for this month. Set one under Budgets & goals.</p>}</motion.div>
        <motion.div className="card" {...rise(6)}><h2>Last 6 months</h2>
          <BarChart data={{ labels: d.monthly.map((m) => m.month), datasets: [{ data: d.monthly.map((m) => m.total), backgroundColor: "#3ddbc8", borderRadius: 8 }] }} options={{ animation: { duration: 1200 }, plugins: { legend: { display: false } }, scales: { x: { grid, ticks: tick }, y: { grid, ticks: tick } } }} /></motion.div>
        <motion.div className="card" {...rise(7)}><h2>Daily spending</h2>
          <Line data={{ labels: d.daily.map((x) => x.date.slice(8)), datasets: [{ data: d.daily.map((x) => x.total), borderColor: "#7c5cff", backgroundColor: "rgba(124,92,255,.2)", fill: true, tension: 0.35 }] }} options={{ animation: { duration: 1400 }, plugins: { legend: { display: false } }, scales: { x: { grid, ticks: tick }, y: { grid, ticks: tick } } }} /></motion.div>
      </div>
    </>
  );
}

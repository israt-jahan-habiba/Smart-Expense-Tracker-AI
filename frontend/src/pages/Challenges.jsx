import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { api, money } from "../api";
import { Confetti, Ring } from "../components.jsx";

export default function Challenges({ user }) {
  const [list, setList] = useState([]);
  const [f, setF] = useState({ name: "30-Day Saving Challenge", days: 30, daily: "" });
  const [boom, setBoom] = useState(0);
  const [err, setErr] = useState("");
  const load = () => api("/challenges").then(setList);
  useEffect(() => { load(); }, []);
  async function check(c) {
    try { const r = await api(`/challenges/${c.id}/checkin`, { method: "POST" }); if ((r.badge && r.badge !== c.badge) || r.completed) setBoom((b) => b + 1); load(); }
    catch (x) { setErr(x.message); }
  }
  return (
    <>
      <Confetti fire={boom} />
      <div className="head"><h1>Saving challenges</h1></div>
      {err && <div className="err" role="alert">{err}</div>}
      <div className="grid g2">
        {list.map((c) => (
          <motion.div className="card stat" key={c.id} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            <Ring pct={(c.done_days / c.days) * 100} size={104}><strong>Day {c.day_number}</strong><div className="muted small">of {c.days}</div></Ring>
            <div style={{ flex: 1 }}>
              <h2 style={{ marginBottom: 4 }}>{c.name}</h2>
              <div>Saved <strong>{money(c.saved, user.currency)}</strong> <span className="muted small">({money(c.daily, user.currency)}/day)</span></div>
              <div className="flames" aria-label={`${c.streak} day streak`}>{c.streak > 0 ? "🔥".repeat(Math.min(c.streak, 7)) : "—"} <span className="muted small">{c.streak} day streak</span></div>
              {c.badge && <div className="pill" style={{ margin: "4px 0" }}>{c.badge}</div>}
              <div className="row" style={{ marginTop: 6 }}>
                <button className="btn sm" disabled={c.checked_today || c.completed || c.expired} onClick={() => check(c)}>{c.completed ? "Completed 🎉" : c.expired ? "Ended" : c.checked_today ? "Saved today ✓" : `I saved ${money(c.daily, user.currency)} today`}</button>
                <button className="btn danger sm" onClick={async () => { await api(`/challenges/${c.id}`, { method: "DELETE" }); load(); }}>Delete</button>
              </div>
            </div>
          </motion.div>
        ))}
        {!list.length && <div className="card muted">No challenges yet. Start one below: small daily saves add up.</div>}
      </div>
      <form className="card row" style={{ marginTop: 16 }} onSubmit={async (e) => { e.preventDefault(); setErr(""); try { await api("/challenges", { method: "POST", body: { name: f.name, days: Number(f.days), daily: Number(f.daily) } }); setF({ ...f, daily: "" }); load(); } catch (x) { setErr(x.message); } }}>
        <label>Challenge name<input value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} required /></label>
        <label>Days<input type="number" min="3" max="365" value={f.days} onChange={(e) => setF({ ...f, days: e.target.value })} /></label>
        <label>Save per day ({user.currency})<input type="number" min="1" required value={f.daily} onChange={(e) => setF({ ...f, daily: e.target.value })} /></label>
        <button className="btn">Start challenge</button>
      </form>
      <p className="muted small">Badges: 🥉 Bronze Saver at 7 days, 🥈 Smart Saver at 15, 🥇 Money Master when you finish.</p>
    </>
  );
}

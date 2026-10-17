import { useEffect, useState } from "react";
import { api, money, thisMonth } from "../api";
import { Bar, Confetti } from "../components.jsx";

export default function Budgets({ user }) {
  const [month, setMonth] = useState(thisMonth());
  const [cats, setCats] = useState([]);
  const [budgets, setBudgets] = useState([]);
  const [goals, setGoals] = useState([]);
  const [b, setB] = useState({ category_id: "", limit: "" });
  const [g, setG] = useState({ name: "", target: "", saved: "", deadline: "" });
  const [err, setErr] = useState("");
  const [boom, setBoom] = useState(0);
  const loadB = () => api(`/budgets?month=${month}`).then(setBudgets);
  const loadG = () => api("/goals").then(setGoals);
  useEffect(() => { api("/categories").then((c) => { setCats(c); setB((x) => ({ ...x, category_id: c[0]?.id })); }); loadG(); }, []);
  useEffect(() => { loadB(); }, [month]);
  const run = (fn) => async (e) => { e.preventDefault(); setErr(""); try { await fn(); } catch (x) { setErr(x.message); } };

  return (
    <>
      <Confetti fire={boom} />
      <div className="head"><h1>Budgets & goals</h1></div>
      {err && <div className="err" role="alert">{err}</div>}
      <div className="grid g2">
        <div className="card"><h2>Monthly budgets</h2>
          <label style={{ maxWidth: 180, marginBottom: 12 }}>Month<input type="month" value={month} onChange={(e) => e.target.value && setMonth(e.target.value)} /></label>
          {budgets.map((x) => (
            <div className="meter" key={x.id}>
              <div className="top"><strong>{x.category}</strong><span className="muted">{money(x.spent, user.currency)} of {money(x.limit, user.currency)} · {x.pct}%</span></div>
              <Bar pct={x.pct} level={x.level} />
              {x.level !== "ok" && <span style={{ color: "var(--coral)", fontSize: ".85rem" }}>{x.level === "exceeded" ? `You crossed your ${x.category} limit.` : `Warning: ${x.pct}% of your ${x.category} budget used.`}</span>}
              <div><button className="btn danger sm" onClick={async () => { await api(`/budgets/${x.id}`, { method: "DELETE" }); loadB(); }}>Remove</button></div>
            </div>
          ))}
          {!budgets.length && <p className="muted">No budgets for {month} yet.</p>}
          <form className="row" onSubmit={run(async () => { await api("/budgets", { method: "PUT", body: { month, category_id: Number(b.category_id), limit: Number(b.limit) } }); setB({ ...b, limit: "" }); loadB(); })}>
            <label>Category<select value={b.category_id} onChange={(e) => setB({ ...b, category_id: e.target.value })}>{cats.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></label>
            <label>Limit ({user.currency})<input type="number" min="1" required value={b.limit} onChange={(e) => setB({ ...b, limit: e.target.value })} /></label>
            <button className="btn">Save budget</button>
          </form>
        </div>
        <div className="card"><h2>Saving goals</h2>
          {goals.map((x) => (
            <div className="meter" key={x.id}>
              <div className="top"><strong>{x.name}</strong><span className="muted">{money(x.saved, user.currency)} of {money(x.target, user.currency)} · {x.pct}%</span></div>
              <Bar pct={x.pct} />{x.pct >= 100 && <div className="ok">🎉 Goal reached!</div>}
              <div className="row">
                <button className="btn ghost sm" onClick={async () => { const a = prompt("Amount to add"); if (a && Number(a) > 0) { const r = await api(`/goals/${x.id}/contribute`, { method: "POST", body: { amount: Number(a) } }); if (r.pct >= 100 && x.pct < 100) setBoom((n) => n + 1); loadG(); } }}>Add savings</button>
                <button className="btn danger sm" onClick={async () => { await api(`/goals/${x.id}`, { method: "DELETE" }); loadG(); }}>Delete</button>
              </div>
            </div>
          ))}
          {!goals.length && <p className="muted">No goals yet. Create one below.</p>}
          <form className="row" onSubmit={run(async () => { await api("/goals", { method: "POST", body: { name: g.name, target: Number(g.target), saved: Number(g.saved || 0), deadline: g.deadline || null } }); setG({ name: "", target: "", saved: "", deadline: "" }); loadG(); })}>
            <label>Goal<input required value={g.name} onChange={(e) => setG({ ...g, name: e.target.value })} placeholder="Buy a laptop" /></label>
            <label>Target<input type="number" min="1" required value={g.target} onChange={(e) => setG({ ...g, target: e.target.value })} /></label>
            <label>Saved so far<input type="number" min="0" value={g.saved} onChange={(e) => setG({ ...g, saved: e.target.value })} /></label>
            <label>Deadline<input type="date" value={g.deadline} onChange={(e) => setG({ ...g, deadline: e.target.value })} /></label>
            <button className="btn">Create goal</button>
          </form>
        </div>
      </div>
    </>
  );
}

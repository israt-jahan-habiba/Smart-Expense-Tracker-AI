import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { api, money } from "../api";
import { Mic } from "../components.jsx";

const lastMonth = () => { const d = new Date(); d.setDate(1); d.setMonth(d.getMonth() - 1); return d.toISOString().slice(0, 7); };
const SUGGEST = ["Can I buy an iPhone this month?", "How can I save more money?", "Why did my spending go up?"];

export default function Insights({ user }) {
  const [ins, setIns] = useState(null);
  const [fc, setFc] = useState(null);
  const [base, setBase] = useState({});
  const [q, setQ] = useState("");
  const [log, setLog] = useState([{ role: "a", text: "Hi! Ask me anything about your money, for example \"Can I buy a laptop this month?\"" }]);
  const [busy, setBusy] = useState(false);
  const end = useRef();
  useEffect(() => { api("/insights").then(setIns); api("/forecast").then(setFc); api(`/dashboard?month=${lastMonth()}`).then((d) => setBase(d.by_category)); }, []);
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }); }, [log, busy]);
  async function ask(text) {
    if (!text.trim() || busy) return;
    setLog((l) => [...l, { role: "u", text }]); setQ(""); setBusy(true);
    try { const r = await api("/ai/chat", { method: "POST", body: { question: text } }); setLog((l) => [...l, { role: "a", text: r.answer, source: r.source }]); }
    catch (x) { setLog((l) => [...l, { role: "a", text: x.message }]); }
    setBusy(false);
  }
  const max = fc ? Math.max(1, ...fc.categories.map((c) => c.prediction)) : 1;
  return (
    <>
      <div className="head"><h1>AI money assistant</h1></div>
      <div className="card"><h2>Chat</h2>
        <div className="row" style={{ marginBottom: 10 }}>{SUGGEST.map((s) => <button key={s} type="button" className="btn ghost sm" style={{ flex: "0 0 auto" }} onClick={() => ask(s)}>{s}</button>)}</div>
        <div className="chat" aria-live="polite">
          {log.map((m, i) => <motion.div key={i} className={`msg ${m.role}`} initial={{ opacity: 0, y: 10, scale: 0.97 }} animate={{ opacity: 1, y: 0, scale: 1 }}>{m.text}
            {m.source === "rules" && <div className="muted small">Data-grounded assistant · answers are calculated from your recorded finances.</div>}</motion.div>)}
          {busy && <div className="msg a dots" aria-label="Assistant is thinking"><span /><span /><span /></div>}
          <div ref={end} />
        </div>
        <form className="row" onSubmit={(e) => { e.preventDefault(); ask(q); }} style={{ marginTop: 10 }}>
          <label>Your question<input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Type or tap the mic" /></label>
          <Mic label="Ask by voice" onText={(t) => ask(t)} /><button className="btn" disabled={busy}>Send</button>
        </form>
        <p className="muted small" style={{ marginBottom: 0 }}>General guidance based on your data, not professional financial advice.</p>
      </div>
      <div className="grid g2" style={{ marginTop: 16 }}>
        <div className="card"><h2>Next month forecast · {fc?.target_month}</h2>
          {fc?.categories.length ? fc.categories.map((c, i) => {
            const b = base[c.category] || 0, arrow = !b ? "→" : c.prediction > b * 1.05 ? "↑" : c.prediction < b * 0.95 ? "↓" : "→";
            return (<div className="fc-row" key={c.category}><span>{c.category}</span>
              <div className="bar"><motion.i initial={{ width: 0 }} animate={{ width: `${(c.prediction / max) * 100}%` }} transition={{ duration: 0.9, delay: i * 0.1 }} /></div>
              <strong style={{ textAlign: "right", color: arrow === "↑" ? "var(--coral)" : arrow === "↓" ? "var(--green)" : "var(--muted)" }}>{money(c.prediction, user.currency)} {arrow}</strong></div>);
          }) : <p className="muted">Needs at least one completed month of expenses.</p>}
          {fc?.categories.length > 0 && <p className="muted small" style={{ marginBottom: 0 }}>Total expected: {money(fc.total, user.currency)}. Each category uses the method with the lowest back-test error. Arrows compare with last month.</p>}
        </div>
        <div className="card"><h2>What your data shows</h2>
          {ins?.length ? ins.map((i, k) => <motion.div key={k} className={`insight ${i.severity}`} initial={{ opacity: 0, x: -12 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: k * 0.08 }}>{i.text}</motion.div>) : <p className="muted">Add a few weeks of expenses to unlock insights.</p>}
          <p className="muted small" style={{ marginBottom: 0 }}>Every number is calculated from your expenses, not guessed by a model.</p>
        </div>
      </div>
    </>
  );
}

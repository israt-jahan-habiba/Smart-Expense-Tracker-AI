import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { api } from "./api";
import { emoji, Mic } from "./components.jsx";

const today = () => new Date().toISOString().slice(0, 10);

export default function EntryModal({ user, onClose, onSaved }) {
  const [cats, setCats] = useState([]);
  const [f, setF] = useState({ amount: "", date: today(), category_id: null, description: "", payment_method: "cash", subcategory: null, receipt_path: null });
  const [text, setText] = useState("");
  const [img, setImg] = useState(null);
  const [busy, setBusy] = useState("");
  const [err, setErr] = useState("");
  useEffect(() => { api("/categories").then((c) => { setCats(c); setF((x) => ({ ...x, category_id: c[0]?.id })); }); }, []);
  useEffect(() => { const k = (e) => e.key === "Escape" && onClose(); addEventListener("keydown", k); return () => removeEventListener("keydown", k); }, []);

  async function parse(t = text) {
    if (!t.trim()) return;
    setBusy("parse"); setErr("");
    try { const p = await api("/ai/parse-expense", { method: "POST", body: { text: t } });
      setF((x) => ({ ...x, amount: p.amount, date: p.date, category_id: p.category_id, description: p.description, subcategory: p.subcategory })); }
    catch (x) { setErr(x.message); }
    setBusy("");
  }
  async function scan(e) {
    const file = e.target.files[0]; if (!file) return;
    setImg(URL.createObjectURL(file)); setBusy("scan"); setErr("");
    const form = new FormData(); form.append("file", file);
    try { const r = await api("/ai/receipt", { method: "POST", form });
      setF((x) => ({ ...x, amount: r.amount ?? "", date: r.date, category_id: r.category_id, description: r.store, subcategory: r.subcategory, receipt_path: r.receipt_path })); }
    catch (x) { setErr(x.message); }
    setBusy("");
  }
  async function save(e) {
    e.preventDefault(); setErr("");
    try { await api("/expenses", { method: "POST", body: { ...f, amount: Number(f.amount), category_id: Number(f.category_id) } }); onSaved(); onClose(); }
    catch (x) { setErr(x.message); }
  }
  return (
    <motion.div className="overlay" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <motion.form className="modal" onSubmit={save} role="dialog" aria-label="Add expense" initial={{ y: 60, scale: 0.94, opacity: 0 }} animate={{ y: 0, scale: 1, opacity: 1 }} transition={{ type: "spring", stiffness: 260, damping: 24 }}>
        <h2 style={{ fontSize: "1.3rem" }}>What did you spend on?</h2>
        <div className="row" style={{ marginTop: 12 }}>
          <label>Say it or type it<input value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), parse())} placeholder="Spent 500 taka on lunch" /></label>
          <Mic label="Speak your expense" onText={(t) => { setText(t); parse(t); }} />
          <button type="button" className="btn ghost" onClick={() => parse()} disabled={busy === "parse"}>{busy === "parse" ? "Reading…" : "Read it"}</button>
        </div>
        <div className="cats" role="radiogroup" aria-label="Category">
          {cats.map((c) => (
            <motion.button type="button" key={c.id} role="radio" aria-checked={f.category_id === c.id} className={`cat ${f.category_id === c.id ? "on" : ""}`}
              whileTap={{ scale: 0.88 }} animate={{ scale: f.category_id === c.id ? 1.07 : 1 }} transition={{ type: "spring", stiffness: 400, damping: 16 }} onClick={() => setF({ ...f, category_id: c.id })}>
              <span>{emoji(c.name)}</span>{c.name}</motion.button>
          ))}
        </div>
        <div className="row">
          <label>Amount ({user.currency})<input type="number" step="0.01" min="0.01" required autoFocus value={f.amount} onChange={(e) => setF({ ...f, amount: e.target.value })} /></label>
          <label>Date<input type="date" required value={f.date} onChange={(e) => setF({ ...f, date: e.target.value })} /></label>
        </div>
        <label style={{ marginTop: 10 }}>Note<input value={f.description} maxLength={255} onChange={(e) => setF({ ...f, description: e.target.value })} /></label>
        <label style={{ marginTop: 10 }}>Or scan a receipt<input type="file" accept="image/*" capture="environment" onChange={scan} /></label>
        {img && <div className={`scanbox ${busy === "scan" ? "scanning" : ""}`}><img src={img} alt="Receipt being scanned" /></div>}
        {busy === "scan" && <p className="muted small">Scanning receipt…</p>}
        {err && <div className="err" role="alert">{err}</div>}
        <div className="row" style={{ marginTop: 14, justifyContent: "flex-end" }}><button type="button" className="btn ghost" onClick={onClose}>Cancel</button><button className="btn">Save expense</button></div>
      </motion.form>
    </motion.div>
  );
}

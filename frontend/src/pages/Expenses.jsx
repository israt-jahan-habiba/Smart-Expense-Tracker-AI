import { useEffect, useState } from "react";
import { api, money } from "../api";
const today = () => new Date().toISOString().slice(0, 10);
const PAY = ["cash", "card", "bkash", "nagad", "bank"];

export default function Expenses({ user }) {
  const [cats, setCats] = useState([]);
  const [rows, setRows] = useState([]);
  const [f, setF] = useState({ q: "", category_id: "", start: "", end: "", min_amount: "", max_amount: "", payment_method: "" });
  const [text, setText] = useState("");
  const [draft, setDraft] = useState(null); // expense being confirmed/edited
  const [msg, setMsg] = useState({ type: "", text: "" });
  const [newCat, setNewCat] = useState("");

  const load = () => {
    const qs = new URLSearchParams(Object.entries(f).filter(([, v]) => v !== ""));
    api(`/expenses?${qs}`).then(setRows).catch((e) => setMsg({ type: "err", text: e.message }));
  };
  useEffect(() => { api("/categories").then(setCats); }, []);
  useEffect(load, [f]);
  const say = (type, text) => setMsg({ type, text });

  async function smartAdd(e) {
    e.preventDefault(); say("", "");
    try {
      const p = await api("/ai/parse-expense", { method: "POST", body: { text } });
      setDraft({ amount: p.amount, date: p.date, category_id: p.category_id, subcategory: p.subcategory || "", payment_method: "cash", description: p.description, note: `Parsed with ${p.source === "llm" ? "AI" : "keyword rules"}. Check and save.` });
      setText("");
    } catch (x) { say("err", x.message); }
  }
  async function save(e) {
    e.preventDefault();
    const { note, id, category, ...body } = draft;
    try {
      await api(id ? `/expenses/${id}` : "/expenses", { method: id ? "PUT" : "POST", body: { ...body, amount: Number(body.amount), category_id: Number(body.category_id), subcategory: body.subcategory || null } });
      say("ok", id ? "Expense updated." : "Expense saved."); setDraft(null); load();
    } catch (x) { say("err", x.message); }
  }
  async function remove(id) {
    if (!confirm("Delete this expense?")) return;
    await api(`/expenses/${id}`, { method: "DELETE" }); say("ok", "Expense deleted."); load();
  }
  async function addCat(e) {
    e.preventDefault();
    try { const c = await api("/categories", { method: "POST", body: { name: newCat } }); setCats([...cats, c]); setNewCat(""); say("ok", `Category "${c.name}" added.`); }
    catch (x) { say("err", x.message); }
  }
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const sd = (k) => (e) => setDraft({ ...draft, [k]: e.target.value });

  return (
    <>
      <div className="head"><h1>Expenses</h1>
        <button className="btn" onClick={() => setDraft({ amount: "", date: today(), category_id: cats[0]?.id, subcategory: "", payment_method: "cash", description: "" })}>Add expense</button></div>
      {msg.text && <div className={msg.type} role="status">{msg.text}</div>}
      <div className="card" style={{ marginBottom: 16 }}>
        <h2>Type it the way you'd say it</h2>
        <form className="row" onSubmit={smartAdd}>
          <label>Describe the expense<input value={text} onChange={(e) => setText(e.target.value)} placeholder="Bought KFC dinner 500 taka" required minLength={2} /></label>
          <button className="btn">Read expense</button>
        </form>
        {draft && (
          <form className="preview" onSubmit={save}>
            {draft.note && <p className="muted" style={{ marginTop: 0 }}>{draft.note}</p>}
            <div className="row">
              <label>Amount ({user.currency})<input type="number" step="0.01" min="0.01" required value={draft.amount} onChange={sd("amount")} /></label>
              <label>Date<input type="date" required value={draft.date} onChange={sd("date")} /></label>
              <label>Category<select value={draft.category_id} onChange={sd("category_id")}>{cats.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></label>
              <label>Payment<select value={draft.payment_method} onChange={sd("payment_method")}>{PAY.map((p) => <option key={p}>{p}</option>)}</select></label>
            </div>
            <div className="row" style={{ marginTop: 10 }}>
              <label>Description<input value={draft.description} onChange={sd("description")} maxLength={255} /></label>
              <button className="btn">Save expense</button>
              <button type="button" className="btn ghost" onClick={() => setDraft(null)}>Cancel</button>
            </div>
          </form>
        )}
      </div>
      <div className="card">
        <h2>Search and filter</h2>
        <div className="row">
          <label>Search<input value={f.q} onChange={set("q")} placeholder="dinner" /></label>
          <label>Category<select value={f.category_id} onChange={set("category_id")}><option value="">All</option>{cats.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></label>
          <label>From<input type="date" value={f.start} onChange={set("start")} /></label>
          <label>To<input type="date" value={f.end} onChange={set("end")} /></label>
          <label>Min<input type="number" value={f.min_amount} onChange={set("min_amount")} /></label>
          <label>Max<input type="number" value={f.max_amount} onChange={set("max_amount")} /></label>
          <label>Payment<select value={f.payment_method} onChange={set("payment_method")}><option value="">Any</option>{PAY.map((p) => <option key={p}>{p}</option>)}</select></label>
        </div>
        <div className="table-wrap" style={{ marginTop: 12 }}>
          <table>
            <thead><tr><th>Date</th><th>Category</th><th>Description</th><th>Payment</th><th className="num">Amount</th><th></th></tr></thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id}><td>{r.date}</td><td><span className="pill">{r.category}</span></td><td>{r.description}</td><td>{r.payment_method}</td>
                  <td className="num">{money(r.amount, user.currency)}</td>
                  <td style={{ whiteSpace: "nowrap" }}>
                    <button className="btn ghost sm" onClick={() => setDraft({ ...r })}>Edit</button>{" "}
                    <button className="btn danger sm" onClick={() => remove(r.id)}>Delete</button></td></tr>
              ))}
              {!rows.length && <tr><td colSpan={6} className="muted">No expenses match. Add one above or loosen the filters.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
      <div className="card" style={{ marginTop: 16 }}>
        <h2>Custom categories</h2>
        <form className="row" onSubmit={addCat}><label>New category<input value={newCat} onChange={(e) => setNewCat(e.target.value)} placeholder="Pets" required /></label><button className="btn">Add category</button></form>
      </div>
    </>
  );
}

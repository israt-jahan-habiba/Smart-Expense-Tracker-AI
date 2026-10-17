import { useState } from "react";
import { api } from "../api";

export default function Profile({ user, setUser }) {
  const [f, setF] = useState({ name: user.name, phone: user.phone || "", monthly_income: user.monthly_income, currency: user.currency, financial_goals: user.financial_goals, budget_preference: user.budget_preference });
  const [msg, setMsg] = useState({ type: "", text: "" });
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  async function save(e) {
    e.preventDefault();
    try { setUser(await api("/me", { method: "PUT", body: { ...f, monthly_income: Number(f.monthly_income), phone: f.phone || null } })); setMsg({ type: "ok", text: "Profile saved." }); }
    catch (x) { setMsg({ type: "err", text: x.message }); }
  }
  return (
    <>
      <div className="head"><h1>Profile</h1></div>
      <form className="card grid" style={{ maxWidth: 560 }} onSubmit={save}>
        <label>Name<input required value={f.name} onChange={set("name")} /></label>
        <label>Phone (optional)<input value={f.phone} onChange={set("phone")} /></label>
        <div className="row">
          <label>Monthly income<input type="number" min="0" value={f.monthly_income} onChange={set("monthly_income")} /></label>
          <label>Currency<select value={f.currency} onChange={set("currency")}>{["BDT", "USD", "EUR", "GBP", "INR"].map((c) => <option key={c}>{c}</option>)}</select></label>
        </div>
        <label>Budget style<select value={f.budget_preference} onChange={set("budget_preference")}><option value="strict">Strict</option><option value="balanced">Balanced</option><option value="flexible">Flexible</option></select></label>
        <label>Financial goals<textarea rows={3} value={f.financial_goals} onChange={set("financial_goals")} placeholder="Save for a laptop, build an emergency fund" /></label>
        {msg.text && <div className={msg.type} role="status">{msg.text}</div>}
        <div><button className="btn">Save profile</button></div>
      </form>
    </>
  );
}

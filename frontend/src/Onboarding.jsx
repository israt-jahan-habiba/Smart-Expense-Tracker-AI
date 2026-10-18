import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { api } from "./api";

const PRIOS = ["Build emergency fund", "Buy something big", "Pay off debt", "Spend less on food", "Invest", "Travel"];
const slide = { initial: { opacity: 0, x: 60 }, animate: { opacity: 1, x: 0 }, exit: { opacity: 0, x: -60 }, transition: { duration: 0.35 } };

function Wallet() {
  return (
    <svg viewBox="0 0 200 160" width="200" aria-hidden="true" style={{ margin: "0 auto" }}>
      {[0, 1, 2].map((i) => (
        <motion.circle key={i} cx={70 + i * 30} r="11" fill="#ffc24b" stroke="#d99a1e" strokeWidth="3" initial={{ cy: -20, opacity: 0 }}
          animate={{ cy: [-20, 62], opacity: [0, 1, 1, 0] }} transition={{ duration: 1.8, delay: i * 0.5, repeat: Infinity, repeatDelay: 0.6 }} />
      ))}
      <motion.g animate={{ y: [0, -4, 0] }} transition={{ duration: 2.4, repeat: Infinity }}>
        <rect x="30" y="64" width="140" height="82" rx="16" fill="#7c5cff" />
        <rect x="30" y="64" width="140" height="22" rx="11" fill="#6445e6" />
        <rect x="120" y="96" width="52" height="30" rx="12" fill="#3ddbc8" /><circle cx="138" cy="111" r="5" fill="#0b2b28" />
      </motion.g>
    </svg>
  );
}

export default function Onboarding({ user, onDone }) {
  const [step, setStep] = useState(0);
  const [income, setIncome] = useState("");
  const [goal, setGoal] = useState({ name: "", target: "" });
  const [prios, setPrios] = useState([]);
  const [err, setErr] = useState("");
  const finish = async () => {
    try {
      await api("/me", { method: "PUT", body: { monthly_income: Number(income || 0), financial_goals: prios.join(", ") } });
      if (goal.name && Number(goal.target) > 0) await api("/goals", { method: "POST", body: { name: goal.name, target: Number(goal.target) } });
      localStorage.setItem(`onboarded_${user.id}`, "1"); onDone();
    } catch (x) { setErr(x.message); }
  };
  return (
    <div className="onb">
      <div className="panel">
        <AnimatePresence mode="wait">
          {step === 0 && <motion.div key="0" {...slide} className="grid"><Wallet /><h1>Take control of your money</h1><p className="muted">A smart companion that tracks, explains and improves your spending.</p></motion.div>}
          {step === 1 && <motion.div key="1" {...slide} className="grid"><h1>Here's how it works</h1>
            <div className="feat">{[["💳", "Track Expenses", "Type or speak your expenses."], ["📊", "Analyze Spending", "See where it goes and why."], ["🚀", "Save Smarter", "Goals, challenges and AI advice."]].map(([i, t, d], k) =>
              <motion.div key={t} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 + k * 0.15 }}>{i} <strong>{t}</strong><div className="muted small">{d}</div></motion.div>)}</div></motion.div>}
          {step === 2 && <motion.div key="2" {...slide} className="grid card" style={{ textAlign: "left" }}><h2>Set up your plan</h2>
            <label>Monthly income<input type="number" min="0" value={income} onChange={(e) => setIncome(e.target.value)} placeholder="50000" /></label>
            <div className="row"><label>Saving goal<input value={goal.name} onChange={(e) => setGoal({ ...goal, name: e.target.value })} placeholder="Laptop" /></label>
              <label>Target<input type="number" min="0" value={goal.target} onChange={(e) => setGoal({ ...goal, target: e.target.value })} placeholder="100000" /></label></div>
            <div><div className="muted small" style={{ marginBottom: 6 }}>Financial priorities</div>
              <div className="prio">{PRIOS.map((p) => <button type="button" key={p} className={prios.includes(p) ? "on" : ""} onClick={() => setPrios(prios.includes(p) ? prios.filter((x) => x !== p) : [...prios, p])}>{p}</button>)}</div></div>
            {err && <div className="err" role="alert">{err}</div>}</motion.div>}
        </AnimatePresence>
        <div className="dotsnav" aria-label={`Step ${step + 1} of 3`}>{[0, 1, 2].map((i) => <i key={i} className={i === step ? "on" : ""} />)}</div>
        <div className="row" style={{ justifyContent: "center" }}>
          {step > 0 && <button className="btn ghost" onClick={() => setStep(step - 1)}>Back</button>}
          {step < 2 ? <button className="btn" onClick={() => setStep(step + 1)}>Continue</button> : <button className="btn" onClick={finish}>Start tracking</button>}
          {step < 2 && <button className="btn ghost" onClick={() => { localStorage.setItem(`onboarded_${user.id}`, "1"); onDone(); }}>Skip</button>}
        </div>
      </div>
    </div>
  );
}

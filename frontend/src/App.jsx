import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { api, getToken, setToken } from "./api";
import { Avatar } from "./components.jsx";
import Onboarding from "./Onboarding.jsx";
import EntryModal from "./EntryModal.jsx";
import Wrapped from "./Wrapped.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Expenses from "./pages/Expenses.jsx";
import Budgets from "./pages/Budgets.jsx";
import Challenges from "./pages/Challenges.jsx";
import Insights from "./pages/Insights.jsx";
import Profile from "./pages/Profile.jsx";

const TABS = [["dashboard", "🏠 Dashboard", Dashboard], ["expenses", "💳 Expenses", Expenses], ["budgets", "🎯 Budgets & goals", Budgets],
  ["challenges", "🔥 Challenges", Challenges], ["insights", "🤖 AI assistant", Insights], ["profile", "👤 Profile", Profile]];
const lastMonth = () => { const d = new Date(); d.setDate(1); d.setMonth(d.getMonth() - 1); return d.toISOString().slice(0, 7); };

function Auth({ onAuth }) {
  const [mode, setMode] = useState("login");
  const [f, setF] = useState({ name: "", email: "", password: "" });
  const [err, setErr] = useState("");
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  async function submit(e) {
    e.preventDefault(); setErr("");
    try { const r = await api(`/auth/${mode}`, { method: "POST", body: mode === "login" ? { email: f.email, password: f.password } : f }); setToken(r.token); onAuth(r.user); }
    catch (x) { setErr(x.message); }
  }
  return (
    <motion.div className="auth" initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }}>
      <form className="card" onSubmit={submit}>
        <h1>💰 Smart Expense Tracker AI</h1>
        <p className="muted" style={{ margin: 0 }}>Your personal AI financial companion.</p>
        {mode === "register" && <label>Name<input required value={f.name} onChange={set("name")} /></label>}
        <label>Email<input type="email" required value={f.email} onChange={set("email")} /></label>
        <label>Password<input type="password" required minLength={8} value={f.password} onChange={set("password")} /></label>
        {err && <div className="err" role="alert">{err}</div>}
        <button className="btn">{mode === "login" ? "Sign in" : "Create account"}</button>
        <button type="button" className="btn ghost" onClick={() => setMode(mode === "login" ? "register" : "login")}>{mode === "login" ? "Create an account" : "I already have an account"}</button>
        <p className="muted small" style={{ margin: 0 }}>Demo: demo@example.com / demo1234 (after running seed.py)</p>
      </form>
    </motion.div>
  );
}

export default function App() {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(!getToken());
  const [tab, setTab] = useState("dashboard");
  const [theme, setTheme] = useState(localStorage.getItem("theme") || "dark");
  const [entry, setEntry] = useState(false);
  const [wrapped, setWrapped] = useState(null);
  const [onb, setOnb] = useState(false);
  const [rev, setRev] = useState(0);
  const [health, setHealth] = useState(null);
  useEffect(() => { document.documentElement.dataset.theme = theme; localStorage.setItem("theme", theme); }, [theme]);
  useEffect(() => { if (getToken()) api("/me").then(setUser).catch(() => setToken(null)).finally(() => setReady(true)); }, []);
  useEffect(() => {
    if (!user) return;
    setOnb(user.monthly_income === 0 && !localStorage.getItem(`onboarded_${user.id}`));
    api("/health-score").then(setHealth).catch(() => {});
  }, [user?.id, rev]);
  if (!ready) return null;
  const shell = (c) => <><div className="blobs" aria-hidden="true"><i /><i /><i /></div>{c}</>;
  if (!user) return shell(<Auth onAuth={setUser} />);
  if (onb) return shell(<Onboarding user={user} onDone={() => { api("/me").then(setUser); setOnb(false); setRev((r) => r + 1); }} />);
  const Page = TABS.find((t) => t[0] === tab)[2];
  return shell(
    <div className="shell">
      <nav className="side glass" aria-label="Main">
        <div className="brand">💰 Smart Finance AI</div>
        {health && <div className="me"><Avatar avatar={health.avatar} /><div><strong>{user.name.split(" ")[0]}</strong><small>{health.level} · {health.score}/100</small></div></div>}
        {TABS.map(([k, label]) => <button key={k} className={`nav ${tab === k ? "on" : ""}`} onClick={() => setTab(k)} aria-current={tab === k ? "page" : undefined}>{label}</button>)}
        <div className="spacer" />
        <button className="nav" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>{theme === "dark" ? "☀️ Light mode" : "🌙 Dark mode"}</button>
        <button className="nav" onClick={() => { setToken(null); setUser(null); }}>Sign out</button>
      </nav>
      <main>
        <AnimatePresence mode="wait">
          <motion.div key={`${tab}-${rev}`} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.25 }}>
            <Page user={user} setUser={setUser} openWrapped={(m) => setWrapped(m || lastMonth())} />
          </motion.div>
        </AnimatePresence>
      </main>
      <motion.button className="fab" onClick={() => setEntry(true)} aria-label="Add expense" whileHover={{ scale: 1.1, rotate: 90 }} whileTap={{ scale: 0.9 }} initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: "spring", delay: 0.5 }}>+</motion.button>
      <AnimatePresence>{entry && <EntryModal user={user} onClose={() => setEntry(false)} onSaved={() => setRev((r) => r + 1)} />}</AnimatePresence>
      {wrapped && <Wrapped month={wrapped} onClose={() => setWrapped(null)} />}
    </div>
  );
}

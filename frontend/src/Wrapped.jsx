import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { api, money } from "./api";
import { Num } from "./components.jsx";

const GRADS = ["linear-gradient(160deg,#7c5cff,#3b2bb0)", "linear-gradient(160deg,#ff6b81,#b3263f)", "linear-gradient(160deg,#16a085,#0b4f6c)", "linear-gradient(160deg,#ffb347,#c4511b)", "linear-gradient(160deg,#243b55,#141e30)"];
const monthName = (m) => new Date(m + "-01").toLocaleString(undefined, { month: "long" });

export default function Wrapped({ month, onClose }) {
  const [d, setD] = useState(null);
  const [i, setI] = useState(0);
  useEffect(() => { api(`/wrapped?month=${month}`).then(setD); }, [month]);
  const slides = d && [
    <><p>Your {monthName(d.month)} Money Report</p><p>You spent</p><div className="big"><Num value={d.total} duration={1.6} /> {d.currency}</div>
      {d.change_pct != null && <p>{d.change_pct > 0 ? "▲" : "▼"} {Math.abs(d.change_pct)}% vs the month before</p>}</>,
    <><p>Your biggest category</p><motion.div className="big" initial={{ scale: 0.4 }} animate={{ scale: 1 }} transition={{ type: "spring" }}>{d.top_emoji} {d.top_category || "—"}</motion.div><p>{d.top_pct}% of everything you spent.</p></>,
    <><p>Your best habit</p><div className="big" style={{ fontSize: "clamp(1.8rem,7vw,3.2rem)" }}>🏆 {d.best_habit}</div>{d.weekend_change_pct != null && <p>Weekend spending {d.weekend_change_pct >= 0 ? "rose" : "fell"} {Math.abs(d.weekend_change_pct)}%.</p>}</>,
    <><p>AI advice</p><div className="big" style={{ fontSize: "clamp(1.6rem,6vw,2.8rem)" }}>💡 {d.advice}</div></>,
    <><p>That's {monthName(d.month)}.</p><div className="big" style={{ fontSize: "clamp(1.8rem,7vw,3.2rem)" }}>Savings rate: {d.savings_rate}%</div><p>Tap to close.</p></>,
  ];
  useEffect(() => { if (!slides) return; const t = setTimeout(() => setI((x) => Math.min(x + 1, slides.length - 1)), 5200); return () => clearTimeout(t); }, [i, !!slides]);
  useEffect(() => { const k = (e) => e.key === "Escape" && onClose(); addEventListener("keydown", k); return () => removeEventListener("keydown", k); }, []);
  if (!slides) return null;
  const next = () => (i < slides.length - 1 ? setI(i + 1) : onClose());
  return (
    <div className="wrapped" style={{ background: GRADS[i % GRADS.length] }} onClick={next} role="dialog" aria-label="Monthly wrapped">
      <div className="wprog">{slides.map((_, k) => <i key={k}><motion.b key={`${k}-${i}`} initial={{ width: k < i ? "100%" : 0 }} animate={{ width: k <= i ? "100%" : 0 }} transition={{ duration: k === i ? 5.2 : 0, ease: "linear" }} /></i>)}</div>
      <button className="wclose" onClick={(e) => { e.stopPropagation(); onClose(); }} aria-label="Close">✕</button>
      <AnimatePresence mode="wait"><motion.div key={i} initial={{ opacity: 0, y: 40 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -40 }} transition={{ duration: 0.4 }}>{slides[i]}</motion.div></AnimatePresence>
    </div>
  );
}

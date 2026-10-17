import { useState } from "react";
import { motion } from "framer-motion";
import { Num, emoji, PALETTE } from "./components.jsx";
import { money } from "./api";

const pt = (r, a) => [160 + r * Math.cos(a), 160 + r * Math.sin(a)];
function slice(r0, r1, a0, a1) {
  const [x0, y0] = pt(r1, a0), [x1, y1] = pt(r1, a1), [x2, y2] = pt(r0, a1), [x3, y3] = pt(r0, a0);
  const l = a1 - a0 > Math.PI ? 1 : 0;
  return `M${x0} ${y0}A${r1} ${r1} 0 ${l} 1 ${x1} ${y1}L${x2} ${y2}A${r0} ${r0} 0 ${l} 0 ${x3} ${y3}Z`;
}

export default function Wheel({ data, prev = {}, currency }) {
  const entries = Object.entries(data);
  const total = entries.reduce((s, [, v]) => s + v, 0);
  const [sel, setSel] = useState(null);
  if (!total) return <p className="muted">No spending this month yet. Tap + to add an expense.</p>;
  const cur = sel && data[sel] != null ? sel : entries[0][0];
  let a = -Math.PI / 2;
  const slices = entries.map(([name, v], i) => {
    const span = (v / total) * Math.PI * 2, a0 = a, a1 = a + span - (entries.length > 1 ? 0.025 : 0.001);
    a += span;
    const mid = (a0 + a1) / 2;
    return { name, v, i, path: slice(62, 142, a0, a1), ox: Math.cos(mid) * 10, oy: Math.sin(mid) * 10 };
  });
  const last = prev[cur] || 0, ch = last ? ((data[cur] - last) / last) * 100 : null;
  return (
    <div className="wheel-wrap">
      <svg viewBox="0 0 320 320" role="img" aria-label="Spending by category">
        {slices.map((s) => (
          <motion.path key={s.name} d={s.path} fill={PALETTE[s.i % PALETTE.length]} tabIndex={0} role="button" aria-label={`${s.name} ${Math.round((s.v / total) * 100)}%`}
            initial={{ opacity: 0, scale: 0.5 }} animate={{ opacity: 1, scale: 1, x: cur === s.name ? s.ox : 0, y: cur === s.name ? s.oy : 0 }}
            transition={{ type: "spring", stiffness: 200, damping: 18, delay: sel ? 0 : s.i * 0.07 }}
            style={{ transformOrigin: "160px 160px" }} onClick={() => setSel(s.name)} onMouseEnter={() => setSel(s.name)} onKeyDown={(e) => e.key === "Enter" && setSel(s.name)} />
        ))}
        <text x="160" y="152" textAnchor="middle" fontSize="30" fill="var(--ink)">{emoji(cur)}</text>
        <text x="160" y="178" textAnchor="middle" fontSize="15" fontWeight="700" fill="var(--ink)">{Math.round((data[cur] / total) * 100)}%</text>
      </svg>
      <div className="detail">
        <h2 style={{ marginBottom: 4 }}>{emoji(cur)} {cur}</h2>
        <div className="muted small">This month</div>
        <div className="big"><Num value={data[cur]} suffix={` ${currency}`} duration={0.6} /></div>
        <div className="muted small" style={{ marginTop: 8 }}>Last month: {money(last, currency)}</div>
        <div style={{ fontWeight: 700 }} className={ch == null ? "muted" : ch > 0 ? "up" : "down"}>
          {ch == null ? "No data last month" : `${ch > 0 ? "▲ +" : "▼ "}${ch.toFixed(0)}% vs last month`}
        </div>
        <div className="legend">{entries.map(([n], i) => <button key={n} className={n === cur ? "on" : ""} onClick={() => setSel(n)}><span style={{ color: PALETTE[i % PALETTE.length] }}>●</span> {n}</button>)}</div>
      </div>
    </div>
  );
}

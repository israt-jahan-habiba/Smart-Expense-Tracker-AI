import { useEffect, useRef, useState } from "react";
import { animate, motion } from "framer-motion";

export const EMOJI = { Food: "🍔", Transportation: "🚗", Shopping: "🛒", Entertainment: "🎬", Healthcare: "🏥", Education: "📚", Bills: "💡", Rent: "🏠", Other: "✨" };
export const emoji = (n) => EMOJI[n] || "🏷️";
export const PALETTE = ["#3ddbc8", "#7c5cff", "#ff6b81", "#ffc24b", "#5b9dff", "#4ade9a", "#e07a3f", "#c084fc", "#94a3b8"];

export function Num({ value = 0, decimals = 0, suffix = "", duration = 1.2 }) {
  const [v, setV] = useState(0);
  const prev = useRef(0);
  useEffect(() => {
    const c = animate(prev.current, value, { duration, ease: "easeOut", onUpdate: setV });
    prev.current = value;
    return () => c.stop();
  }, [value]);
  return <span>{v.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}{suffix}</span>;
}

export function Ring({ pct = 0, size = 110, stroke = 10, color = "var(--teal)", children }) {
  const r = (size - stroke) / 2, c = 2 * Math.PI * r, p = Math.max(0, Math.min(100, pct));
  return (
    <div className="ring" style={{ width: size, height: size, flex: "0 0 auto" }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--track)" strokeWidth={stroke} />
        <motion.circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth={stroke} strokeLinecap="round" strokeDasharray={c}
          initial={{ strokeDashoffset: c }} animate={{ strokeDashoffset: c * (1 - p / 100) }} transition={{ duration: 1.3, ease: "easeOut" }} />
      </svg>
      <div className="ring-in">{children}</div>
    </div>
  );
}

export function Bar({ pct, level = "" }) {
  return <div className={`bar ${level}`}><motion.i initial={{ width: 0 }} animate={{ width: `${Math.min(100, pct)}%` }} transition={{ duration: 1, ease: "easeOut" }} /></div>;
}

export function Confetti({ fire }) {
  const ref = useRef();
  useEffect(() => {
    if (!fire || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const cv = ref.current, ctx = cv.getContext("2d");
    cv.width = innerWidth; cv.height = innerHeight;
    const ps = Array.from({ length: 150 }, () => ({ x: innerWidth / 2, y: innerHeight * 0.45, vx: (Math.random() - 0.5) * 16, vy: -Math.random() * 14 - 3, s: 6 + Math.random() * 6, c: `hsl(${Math.random() * 360} 90% 60%)`, r: Math.random() * 6 }));
    let id, t = 0;
    const tick = () => {
      ctx.clearRect(0, 0, cv.width, cv.height); t++;
      ps.forEach((p) => { p.vy += 0.35; p.x += p.vx; p.y += p.vy; p.r += 0.2; ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.r); ctx.fillStyle = p.c; ctx.fillRect(-p.s / 2, -p.s / 2, p.s, p.s * 0.6); ctx.restore(); });
      if (t < 170) id = requestAnimationFrame(tick); else ctx.clearRect(0, 0, cv.width, cv.height);
    };
    tick();
    return () => cancelAnimationFrame(id);
  }, [fire]);
  return <canvas ref={ref} className="confetti" aria-hidden="true" />;
}

export function Mic({ onText, label = "Speak" }) {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const [on, setOn] = useState(false);
  const start = () => {
    if (!SR) return;
    const r = new SR();
    r.lang = "en-US"; r.interimResults = false;
    r.onresult = (e) => onText(e.results[0][0].transcript);
    r.onend = () => setOn(false); r.onerror = () => setOn(false);
    setOn(true); r.start();
  };
  return <button type="button" className={`mic ${on ? "live" : ""}`} onClick={start} disabled={!SR} aria-label={label} title={SR ? label : "Voice input is not supported in this browser (try Chrome or Edge)"}>🎤</button>;
}

export function Avatar({ avatar, size = "2rem" }) {
  return <motion.span key={avatar} initial={{ scale: 0.3, rotate: -20 }} animate={{ scale: 1, rotate: 0 }} transition={{ type: "spring", stiffness: 260, damping: 12 }} style={{ fontSize: size, display: "inline-block" }}>{avatar}</motion.span>;
}

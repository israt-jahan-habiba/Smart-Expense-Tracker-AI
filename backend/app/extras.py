"""Gamified / storytelling features: health score, money story, wrapped, challenges, smart notifications, purchase check."""
import math, re, statistics
from calendar import monthrange
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.orm import Session
from .db import get_db, User, Expense, Goal, Challenge
from .security import current_user
from .services import analytics as A

router = APIRouter(prefix="/api")
EMOJI = {"Food": "🍔", "Transportation": "🚗", "Shopping": "🛒", "Entertainment": "🎬", "Healthcare": "🏥", "Education": "📚", "Bills": "💡", "Rent": "🏠", "Other": "✨"}
LEVELS = [(0, "Money Rookie", "😟"), (40, "Getting There", "🙂"), (60, "Smart Saver", "😎"), (80, "Financial Expert", "🤑")]


def last_month() -> str:
    return A.shift_month(A.this_month(), -1)


def total(db, uid, m) -> float:
    return sum(A.spent_by_category(db, uid, m).values()) / 100


def weekend_total(db, u, m) -> float:
    s, e = A.month_bounds(m)
    wk = {4, 5} if u.currency == "BDT" else {5, 6}  # Fri/Sat in Bangladesh, Sat/Sun elsewhere
    rows = db.query(Expense).filter(Expense.user_id == u.id, Expense.date >= s, Expense.date < e)
    return sum(x.amount_minor for x in rows if x.date.weekday() in wk) / 100


def pct_change(new, old):
    return round((new - old) / old * 100, 1) if old else None


@router.get("/health-score")
def health_score(u: User = Depends(current_user), db: Session = Depends(get_db)):
    cur, last = A.this_month(), last_month()
    inc = u.monthly_income_minor / 100
    rate = (inc - total(db, u.id, last)) / inc * 100 if inc else 0
    s_save = max(0, min(100, rate / 20 * 100))
    bs = A.budget_status(db, u.id, cur)
    s_budget = 70 if not bs else sum(100 if b["pct"] < 90 else 60 if b["pct"] < 100 else 20 for b in bs) / len(bs)
    totals = [t for t in (total(db, u.id, A.shift_month(cur, -i)) for i in range(1, 5)) if t > 0]
    s_stab = max(0, 100 - statistics.pstdev(totals) / statistics.mean(totals) * 250) if len(totals) >= 3 else 60
    score = round(0.4 * s_save + 0.3 * s_budget + 0.3 * s_stab)
    lvl = [l for l in LEVELS if score >= l[0]][-1]
    return {"score": score, "level": lvl[1], "avatar": lvl[2], "savings_rate": round(rate, 1),
            "parts": [{"label": "Savings rate", "value": round(s_save)}, {"label": "Budget control", "value": round(s_budget)}, {"label": "Steady spending", "value": round(s_stab)}]}


def summary(db, u, m) -> dict:
    by, prev = A.spent_by_category(db, u.id, m), A.spent_by_category(db, u.id, A.shift_month(m, -1))
    by, prev = {k: v / 100 for k, v in by.items()}, {k: v / 100 for k, v in prev.items()}
    tot, ptot = sum(by.values()), sum(prev.values())
    inc = u.monthly_income_minor / 100
    rate = (inc - tot) / inc * 100 if inc else 0
    inc_cat = max(by, key=lambda c: by[c] - prev.get(c, 0)) if by else None
    wk, pwk = weekend_total(db, u, m), weekend_total(db, u, A.shift_month(m, -1))
    top = max(by, key=by.get) if by else None
    s, e = A.month_bounds(m)
    days = len({x.date for x in db.query(Expense.date).filter(Expense.user_id == u.id, Expense.date >= s, Expense.date < e)})
    if rate >= 20: habit = f"Saved {rate:.0f}% of income"
    elif tot and ptot and tot < ptot: habit = f"Spent {abs(pct_change(tot, ptot)):.0f}% less than last month"
    else: habit = f"Logged expenses on {days} different days"
    disc = {c: v for c, v in by.items() if c in ("Shopping", "Entertainment", "Food")} or by
    adv_cat = max(disc, key=disc.get) if disc else None
    advice = f"Reduce {adv_cat} spending by 15% to save about {round(disc[adv_cat] * .15, -1):,.0f} {u.currency}." if adv_cat else "Add expenses to get personalised advice."
    return {"month": m, "currency": u.currency, "total": round(tot, 2), "prev_total": round(ptot, 2), "change_pct": pct_change(tot, ptot),
            "top_category": top, "top_emoji": EMOJI.get(top, "✨"), "top_pct": round(by[top] / tot * 100) if top else 0,
            "biggest_increase": inc_cat, "increase_amount": round(by[inc_cat] - prev.get(inc_cat, 0), 2) if inc_cat else 0,
            "weekend_change_pct": pct_change(wk, pwk), "savings_rate": round(rate, 1), "best_habit": habit, "advice": advice}


@router.get("/story")
def story(u: User = Depends(current_user), db: Session = Depends(get_db)):
    m = last_month()
    s = summary(db, u, m)
    lines = []
    if s["biggest_increase"] and s["increase_amount"] > 0:
        lines.append(f"You spent {s['increase_amount']:,.0f} {u.currency} more on {s['biggest_increase']} in {m} than the month before.")
    if s["weekend_change_pct"] is not None:
        lines.append(f"Your weekend spending {'rose' if s['weekend_change_pct'] >= 0 else 'fell'} by {abs(s['weekend_change_pct']):.0f}%.")
    if s["top_category"]:
        lines.append(f"{s['top_emoji']} {s['top_category']} took {s['top_pct']}% of your budget.")
    lines.append(f"Best habit: {s['best_habit']}.")
    return {"month": m, "lines": lines}


@router.get("/wrapped")
def wrapped(month: Optional[str] = None, u: User = Depends(current_user), db: Session = Depends(get_db)):
    if month and not re.match(r"^\d{4}-(0[1-9]|1[0-2])$", month):
        raise HTTPException(422, "month must be YYYY-MM")
    return summary(db, u, month or last_month())


# ---------- Smart notifications ----------
@router.get("/notifications")
def notifications(u: User = Depends(current_user), db: Session = Depends(get_db)):
    cur, today = A.this_month(), date.today()
    frac = today.day / monthrange(today.year, today.month)[1]
    now = {k: v / 100 for k, v in A.spent_by_category(db, u.id, cur).items()}
    hist = [{k: v / 100 for k, v in A.spent_by_category(db, u.id, A.shift_month(cur, -i)).items()} for i in (1, 2, 3)]
    goal = next((g for g in db.query(Goal).filter(Goal.user_id == u.id) if g.saved_minor < g.target_minor), None)
    out = []
    for c, v in sorted(now.items(), key=lambda kv: -kv[1]):
        base = [h[c] for h in hist if c in h]
        if base and frac >= 0.3:
            usual = sum(base) / len(base)
            over = (v / frac - usual) / usual * 100
            if over >= 40:
                cut = round(v / frac * 0.15, -2) or 100
                tail = f" Reducing it by {cut:,.0f} {u.currency} can help you reach your {goal.name} goal faster." if goal else f" Trimming {cut:,.0f} {u.currency} would put you back on track."
                out.append({"level": "warn", "icon": "⚠️", "text": f"Hey! Your {c} spending is on pace to be {over:.0f}% higher than usual.{tail}"})
    for b in A.budget_status(db, u.id, cur):
        if b["level"] == "exceeded":
            out.append({"level": "warn", "icon": "🚨", "text": f"You've passed your {b['category']} budget ({b['pct']:.0f}%). Pause {b['category'].lower()} spending for a few days to recover."})
        elif b["level"] == "warning":
            out.append({"level": "warn", "icon": "👀", "text": f"{b['pct']:.0f}% of your {b['category']} budget is gone, and there are still days left this month."})
    for g in db.query(Goal).filter(Goal.user_id == u.id):
        if g.target_minor and g.saved_minor / g.target_minor >= 0.9 and g.saved_minor < g.target_minor:
            out.append({"level": "good", "icon": "🎯", "text": f"So close! Just {(g.target_minor - g.saved_minor) / 100:,.0f} {u.currency} more for '{g.name}'."})
    if not out:
        out.append({"level": "good", "icon": "✅", "text": "You're on track this month. Nothing needs your attention."})
    return out


# ---------- Saving challenges ----------
class ChallengeIn(BaseModel):
    name: str = Field("30-Day Saving Challenge", max_length=120)
    days: int = Field(30, ge=3, le=365)
    daily: float = Field(gt=0)


def ch_out(c: Challenge) -> dict:
    done = sorted({int(x) for x in c.checkins.split(",") if x})
    today_no = (date.today() - c.start_date).days + 1
    streak, d = 0, today_no if today_no in done else today_no - 1
    while d in done:
        streak, d = streak + 1, d - 1
    n = len(done)
    badge = "🥇 Money Master" if n >= c.days else "🥈 Smart Saver" if n >= 15 else "🥉 Bronze Saver" if n >= 7 else None
    return {"id": c.id, "name": c.name, "days": c.days, "daily": c.daily_minor / 100, "day_number": min(max(today_no, 1), c.days),
            "done_days": n, "saved": n * c.daily_minor / 100, "streak": streak, "badge": badge, "checked_today": today_no in done,
            "completed": n >= c.days, "expired": today_no > c.days and n < c.days}


@router.get("/challenges")
def get_challenges(u: User = Depends(current_user), db: Session = Depends(get_db)):
    return [ch_out(c) for c in db.query(Challenge).filter(Challenge.user_id == u.id).order_by(Challenge.id.desc())]


@router.post("/challenges", status_code=201)
def new_challenge(body: ChallengeIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    c = Challenge(user_id=u.id, name=body.name, days=body.days, daily_minor=int(round(body.daily * 100)), start_date=date.today())
    db.add(c); db.commit()
    return ch_out(c)


@router.post("/challenges/{cid}/checkin")
def checkin(cid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    c = db.get(Challenge, cid)
    if not c or c.user_id != u.id:
        raise HTTPException(404, "Challenge not found")
    n = (date.today() - c.start_date).days + 1
    if n > c.days:
        raise HTTPException(400, "This challenge has ended")
    done = {int(x) for x in c.checkins.split(",") if x} | {n}
    c.checkins = ",".join(map(str, sorted(done)))
    db.commit()
    return ch_out(c)


@router.delete("/challenges/{cid}", status_code=204)
def del_challenge(cid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    c = db.get(Challenge, cid)
    if not c or c.user_id != u.id:
        raise HTTPException(404, "Challenge not found")
    db.delete(c); db.commit()


# ---------- "Can I buy X?" ----------
CATALOG = {"iphone": 130000, "macbook": 200000, "laptop": 90000, "phone": 40000, "tv": 60000, "bike": 50000}


def purchase_check(db, u, question: str):
    q = question.lower()
    if not re.search(r"\b(buy|afford|purchase|get)\b", q):
        return None
    m = re.search(r"(\d[\d,]*(?:\.\d+)?)\s*(k)?\b", q)
    price, est = None, False
    if m:
        price = float(m.group(1).replace(",", "")) * (1000 if m.group(2) else 1)
    else:
        for k, v in CATALOG.items():
            if k in q:
                price, est = v, True
                break
    if not price:
        return None
    cur = A.this_month()
    inc = u.monthly_income_minor / 100
    avg = [t for t in (total(db, u.id, A.shift_month(cur, -i)) for i in (1, 2, 3)) if t > 0]
    spend = sum(avg) / len(avg) if avg else total(db, u.id, cur)
    surplus = inc - spend
    c = u.currency
    note = f" (using a typical price of {price:,.0f} {c}, since you didn't give one)" if est else ""
    if surplus <= 0:
        verdict = f"Right now your average spending ({spend:,.0f} {c}) is at or above your income, so I'd hold off on a {price:,.0f} {c} purchase{note} until you've freed up some monthly surplus."
    elif price <= surplus * 0.5:
        verdict = f"Yes, this looks affordable{note}. It's about {price / surplus * 100:.0f}% of your monthly surplus of {surplus:,.0f} {c}, so your emergency savings stay intact."
    elif price <= surplus:
        verdict = f"Possible, but it would use {price / surplus * 100:.0f}% of your {surplus:,.0f} {c} monthly surplus{note} and cut into your emergency savings. Consider waiting a month."
    else:
        verdict = f"Based on your spending pattern, buying it now{note} may drain your emergency savings. Your surplus is about {surplus:,.0f} {c}/month, so consider saving for {math.ceil(price / surplus)} more months."
    return {"price": price, "monthly_surplus": round(surplus, 2), "verdict": verdict}

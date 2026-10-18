from collections import defaultdict
from datetime import date, timedelta
import numpy as np
from sklearn.linear_model import LinearRegression
from sqlalchemy.orm import Session
from ..db import Expense, Budget, User


def shift_month(m: str, n: int) -> str:
    y, mo = map(int, m.split("-"))
    i = y * 12 + mo - 1 + n
    return f"{i // 12}-{i % 12 + 1:02d}"


def month_bounds(m: str):
    y, mo = map(int, m.split("-"))
    return date(y, mo, 1), date(y + (mo == 12), mo % 12 + 1, 1)


def this_month() -> str:
    return date.today().strftime("%Y-%m")


def spent_by_category(db: Session, uid: int, month: str) -> dict[str, int]:
    s, e = month_bounds(month)
    out: dict[str, int] = defaultdict(int)
    for x in db.query(Expense).filter(Expense.user_id == uid, Expense.date >= s, Expense.date < e):
        out[x.category.name if x.category else "Uncategorized"] += x.amount_minor
    return dict(out)


def budget_status(db: Session, uid: int, month: str) -> list[dict]:
    spent = spent_by_category(db, uid, month)
    res = []
    for b in db.query(Budget).filter(Budget.user_id == uid, Budget.month == month):
        sp = spent.get(b.category.name, 0)
        pct = round(sp / b.limit_minor * 100, 1) if b.limit_minor else 0
        res.append({"id": b.id, "category_id": b.category_id, "category": b.category.name, "limit": b.limit_minor / 100,
                    "spent": sp / 100, "pct": pct, "level": "exceeded" if pct >= 100 else "warning" if pct >= 90 else "ok"})
    return sorted(res, key=lambda r: -r["pct"])


# ---------- Forecasting: pick best of naive / moving average / linear regression by backtest MAE ----------
def _predict(method: str, hist: list[float]) -> float:
    if method == "naive":
        return hist[-1]
    if method == "moving_average":
        return float(np.mean(hist[-3:]))
    x = np.arange(len(hist)).reshape(-1, 1)
    return float(LinearRegression().fit(x, hist).predict([[len(hist)]])[0])


def forecast_series(series: list[float]) -> dict:
    if len(series) < 2:
        return {"prediction": series[-1] if series else 0.0, "method": "naive", "mae": None, "naive_mae": None}
    methods = ["naive", "moving_average", "linear_regression"]
    errors = {m: [] for m in methods}
    for i in range(3, len(series)):  # walk-forward backtest, needs >= 4 points
        for m in methods:
            errors[m].append(abs(_predict(m, series[:i]) - series[i]))
    if errors["naive"]:
        maes = {m: float(np.mean(v)) for m, v in errors.items()}
        best = min(maes, key=maes.get)
        mae, naive_mae = maes[best], maes["naive"]
    else:
        best, mae, naive_mae = "moving_average", None, None
    return {"prediction": max(0.0, _predict(best, series)), "method": best, "mae": mae, "naive_mae": naive_mae}


def forecast(db: Session, uid: int, months_back: int = 6) -> dict:
    """Forecast next month from COMPLETED months only (the current month is partial)."""
    cur = this_month()
    months = [shift_month(cur, -i) for i in range(months_back, 0, -1)]
    data = {m: spent_by_category(db, uid, m) for m in months}
    first = next((i for i, m in enumerate(months) if data[m]), None)
    if first is None:
        return {"target_month": shift_month(cur, 1), "categories": [], "total": 0, "months_used": 0}
    months = months[first:]
    cats = sorted({c for m in months for c in data[m]})
    rows = []
    for c in cats:
        r = forecast_series([data[m].get(c, 0) / 100 for m in months])
        rows.append({"category": c, **{k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items()}})
    rows.sort(key=lambda r: -r["prediction"])
    return {"target_month": shift_month(cur, 1), "months_used": len(months), "categories": rows,
            "total": round(sum(r["prediction"] for r in rows), 2)}


# ---------- Insights: computed in code so numbers are never hallucinated ----------
def insights(db: Session, user: User) -> list[dict]:
    out, uid, cur = [], user.id, this_month()
    last, prev = shift_month(cur, -1), shift_month(cur, -2)
    a, b = spent_by_category(db, uid, last), spent_by_category(db, uid, prev)
    for c in sorted(a, key=lambda c: -a[c]):
        if b.get(c, 0) > 0:
            ch = (a[c] - b[c]) / b[c] * 100
            if abs(ch) >= 20:
                out.append({"type": "trend", "severity": "warn" if ch > 0 else "good", "category": c, "change_pct": round(ch, 1),
                            "text": f"Your {c} spending {'increased' if ch > 0 else 'decreased'} by {abs(ch):.0f}% in {last} compared to {prev}."})
    if a:
        top = max(a, key=a.get)
        out.append({"type": "top_category", "severity": "info", "text": f"{top} was your biggest category in {last} ({a[top]/sum(a.values())*100:.0f}% of spending)."})
    since = date.today() - timedelta(days=90)
    rows = db.query(Expense).filter(Expense.user_id == uid, Expense.date >= since).all()
    if len(rows) >= 10:
        wd = defaultdict(int)
        for x in rows:
            wd[x.date.strftime("%A")] += x.amount_minor
        tot = sum(wd.values())
        day = max(wd, key=wd.get)
        out.append({"type": "weekday", "severity": "info", "text": f"{day} is your highest-spending day ({wd[day]/tot*100:.0f}% of the last 90 days)."})
        wk = (wd["Saturday"] + wd["Sunday"]) / tot * 100
        if wk > 35:
            out.append({"type": "weekend", "severity": "warn", "text": f"{wk:.0f}% of your spending happens on weekends."})
    for bs in budget_status(db, uid, cur):
        if bs["level"] != "ok":
            out.append({"type": "budget", "severity": "warn", "text": f"You have used {bs['pct']:.0f}% of your {bs['category']} budget this month."})
    if user.monthly_income_minor and a:
        rate = (user.monthly_income_minor - sum(a.values())) / user.monthly_income_minor * 100
        out.append({"type": "savings", "severity": "good" if rate >= 20 else "warn", "text": f"Your savings rate in {last} was {rate:.0f}% of income (a common target is 20%)."})
    return out


def build_facts(db: Session, user: User) -> dict:
    cur = this_month()
    return {"currency": user.currency, "monthly_income": user.monthly_income_minor / 100, "goals": user.financial_goals,
            "this_month_by_category": {k: v / 100 for k, v in spent_by_category(db, user.id, cur).items()},
            "last_month_by_category": {k: v / 100 for k, v in spent_by_category(db, user.id, shift_month(cur, -1)).items()},
            "budgets": budget_status(db, user.id, cur), "insights": insights(db, user),
            "forecast_next_month": forecast(db, user.id)["categories"][:5]}

import os, re, uuid
from collections import defaultdict
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, FastAPI, File, HTTPException, Query, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from .db import Base, engine, get_db, User, Category, Expense, Budget, Goal
from .security import hash_password, verify_password, make_token, current_user
from .services import analytics as A, nlp, llm, ocr, reports
from .extras import router as extras_router, purchase_check

Base.metadata.create_all(engine)
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
DEFAULT_CATS = nlp.CATEGORIES

app = FastAPI(title="Smart Expense Tracker API")
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
api = APIRouter(prefix="/api")
MONTH = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def minor(x: float) -> int:
    return int(round(x * 100))


def check_month(m: Optional[str]) -> str:
    m = m or A.this_month()
    if not MONTH.match(m):
        raise HTTPException(422, "month must be YYYY-MM")
    return m


def user_out(u: User) -> dict:
    return {"id": u.id, "name": u.name, "email": u.email, "phone": u.phone, "monthly_income": u.monthly_income_minor / 100,
            "currency": u.currency, "financial_goals": u.financial_goals, "budget_preference": u.budget_preference}


def ex_out(e: Expense) -> dict:
    return {"id": e.id, "amount": e.amount_minor / 100, "date": e.date.isoformat(), "category_id": e.category_id,
            "category": e.category.name if e.category else "Uncategorized", "subcategory": e.subcategory,
            "payment_method": e.payment_method, "description": e.description, "receipt_path": e.receipt_path}


def own_category(db: Session, u: User, cid: int) -> Category:
    c = db.get(Category, cid)
    if not c or c.user_id != u.id:
        raise HTTPException(404, "Category not found")
    return c


def category_by_name(db: Session, u: User, name: str) -> Category:
    c = db.query(Category).filter(Category.user_id == u.id, Category.name.ilike(name)).first()
    if not c:
        c = db.query(Category).filter(Category.user_id == u.id, Category.name == "Other").first()
    return c


# ---------------- Auth & profile ----------------
class RegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    phone: Optional[str] = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class ProfileIn(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    monthly_income: Optional[float] = Field(None, ge=0)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    financial_goals: Optional[str] = None
    budget_preference: Optional[str] = None


def create_user(db: Session, name, email, password, phone=None, income=0.0) -> User:
    u = User(name=name, email=email.strip().lower(), phone=phone, password_hash=hash_password(password), monthly_income_minor=minor(income))
    db.add(u)
    db.flush()
    db.add_all([Category(user_id=u.id, name=n, is_default=True) for n in DEFAULT_CATS])
    db.commit()
    return u


@api.post("/auth/register", status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(409, "Email already registered")
    u = create_user(db, body.name, email, body.password, body.phone)
    return {"token": make_token(u.id), "user": user_out(u)}


@api.post("/auth/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    u = db.query(User).filter(User.email == email).first()
    if not u or not verify_password(body.password, u.password_hash):
        raise HTTPException(401, "Incorrect email or password")
    return {"token": make_token(u.id), "user": user_out(u)}


@api.get("/me")
def me(u: User = Depends(current_user)):
    return user_out(u)


@api.put("/me")
def update_me(body: ProfileIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    d = body.model_dump(exclude_unset=True)
    if "monthly_income" in d:
        u.monthly_income_minor = minor(d.pop("monthly_income"))
    if "currency" in d:
        d["currency"] = d["currency"].upper()
    for k, v in d.items():
        setattr(u, k, v)
    db.commit()
    return user_out(u)


# ---------------- Categories ----------------
class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)


@api.get("/categories")
def list_categories(u: User = Depends(current_user), db: Session = Depends(get_db)):
    return [{"id": c.id, "name": c.name, "is_default": c.is_default} for c in db.query(Category).filter(Category.user_id == u.id).order_by(Category.id)]


@api.post("/categories", status_code=201)
def add_category(body: CategoryIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    if db.query(Category).filter(Category.user_id == u.id, Category.name.ilike(body.name)).first():
        raise HTTPException(409, "Category already exists")
    c = Category(user_id=u.id, name=body.name.strip())
    db.add(c)
    db.commit()
    return {"id": c.id, "name": c.name, "is_default": False}


@api.delete("/categories/{cid}", status_code=204)
def delete_category(cid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    c = own_category(db, u, cid)
    if c.is_default:
        raise HTTPException(400, "Default categories cannot be deleted")
    other = category_by_name(db, u, "Other")
    db.query(Expense).filter(Expense.category_id == cid).update({"category_id": other.id})
    db.query(Budget).filter(Budget.category_id == cid).delete()
    db.delete(c)
    db.commit()
    return Response(status_code=204)


# ---------------- Expenses ----------------
class ExpenseIn(BaseModel):
    amount: float = Field(gt=0, lt=1e9)
    date: date
    category_id: int
    subcategory: Optional[str] = None
    payment_method: str = "cash"
    description: str = Field("", max_length=255)
    receipt_path: Optional[str] = None


@api.get("/expenses")
def list_expenses(q: Optional[str] = None, category_id: Optional[int] = None, start: Optional[date] = None, end: Optional[date] = None,
                  min_amount: Optional[float] = None, max_amount: Optional[float] = None, payment_method: Optional[str] = None,
                  limit: int = Query(200, le=1000), u: User = Depends(current_user), db: Session = Depends(get_db)):
    qs = db.query(Expense).filter(Expense.user_id == u.id)
    if q:
        qs = qs.filter(Expense.description.ilike(f"%{q}%"))
    if category_id:
        qs = qs.filter(Expense.category_id == category_id)
    if start:
        qs = qs.filter(Expense.date >= start)
    if end:
        qs = qs.filter(Expense.date <= end)
    if min_amount is not None:
        qs = qs.filter(Expense.amount_minor >= minor(min_amount))
    if max_amount is not None:
        qs = qs.filter(Expense.amount_minor <= minor(max_amount))
    if payment_method:
        qs = qs.filter(Expense.payment_method == payment_method)
    return [ex_out(e) for e in qs.order_by(Expense.date.desc(), Expense.id.desc()).limit(limit)]


@api.post("/expenses", status_code=201)
def add_expense(body: ExpenseIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    own_category(db, u, body.category_id)
    e = Expense(user_id=u.id, amount_minor=minor(body.amount), **body.model_dump(exclude={"amount"}))
    db.add(e)
    db.commit()
    db.refresh(e)
    return ex_out(e)


def own_expense(db, u, eid) -> Expense:
    e = db.get(Expense, eid)
    if not e or e.user_id != u.id:
        raise HTTPException(404, "Expense not found")
    return e


@api.put("/expenses/{eid}")
def edit_expense(eid: int, body: ExpenseIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    e = own_expense(db, u, eid)
    own_category(db, u, body.category_id)
    for k, v in body.model_dump(exclude={"amount"}).items():
        setattr(e, k, v)
    e.amount_minor = minor(body.amount)
    db.commit()
    return ex_out(e)


@api.delete("/expenses/{eid}", status_code=204)
def delete_expense(eid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    db.delete(own_expense(db, u, eid))
    db.commit()
    return Response(status_code=204)


# ---------------- AI: parsing, receipts, advisor ----------------
class ParseIn(BaseModel):
    text: str = Field(min_length=2, max_length=500)


@api.post("/ai/parse-expense")
def parse_expense(body: ParseIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    try:
        p = nlp.parse_expense(body.text, u.currency)
    except ValueError as ex:
        raise HTTPException(422, f"{ex}. Include an amount, e.g. 'Uber 300 taka'.")
    c = category_by_name(db, u, p["category"])
    return {**p, "category_id": c.id, "category": c.name}


@api.post("/ai/receipt")
async def scan_receipt(file: UploadFile = File(...), u: User = Depends(current_user), db: Session = Depends(get_db)):
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(415, "Upload a JPG, PNG or WebP image")
    data = await file.read()
    if len(data) > 8 * 1024 * 1024:
        raise HTTPException(413, "Image must be under 8 MB")
    name = f"{u.id}_{uuid.uuid4().hex}.{file.content_type.split('/')[1]}"
    with open(os.path.join(UPLOAD_DIR, name), "wb") as f:
        f.write(data)
    try:
        r = ocr.scan(data)
    except ocr.OCRUnavailable as ex:
        raise HTTPException(501, "Could not read the receipt. Quick fix: run 'pip install rapidocr-onnxruntime' in the backend environment and restart the server "
                                 f"(or install Tesseract, see README). Details: {ex}")
    c = category_by_name(db, u, r["category"])
    return {**r, "category_id": c.id, "category": c.name, "receipt_path": name}


class ChatIn(BaseModel):
    question: str = Field(min_length=2, max_length=500)


@api.post("/ai/chat")
def chat(body: ChatIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    facts = A.build_facts(db, u)
    pc = purchase_check(db, u, body.question)
    if pc:
        facts["purchase_check"] = pc
    answer, source = llm.advise(body.question, facts)
    return {"answer": answer, "source": source}


@api.get("/insights")
def get_insights(u: User = Depends(current_user), db: Session = Depends(get_db)):
    return A.insights(db, u)


@api.get("/forecast")
def get_forecast(u: User = Depends(current_user), db: Session = Depends(get_db)):
    return A.forecast(db, u.id)


# ---------------- Budgets, goals, alerts ----------------
class BudgetIn(BaseModel):
    category_id: int
    month: str
    limit: float = Field(gt=0)


@api.get("/budgets")
def get_budgets(month: Optional[str] = None, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return A.budget_status(db, u.id, check_month(month))


@api.put("/budgets")
def set_budget(body: BudgetIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    check_month(body.month)
    own_category(db, u, body.category_id)
    b = db.query(Budget).filter_by(user_id=u.id, category_id=body.category_id, month=body.month).first()
    if b:
        b.limit_minor = minor(body.limit)
    else:
        db.add(Budget(user_id=u.id, category_id=body.category_id, month=body.month, limit_minor=minor(body.limit)))
    db.commit()
    return A.budget_status(db, u.id, body.month)


@api.delete("/budgets/{bid}", status_code=204)
def delete_budget(bid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    b = db.get(Budget, bid)
    if not b or b.user_id != u.id:
        raise HTTPException(404, "Budget not found")
    db.delete(b)
    db.commit()
    return Response(status_code=204)


class GoalIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    target: float = Field(gt=0)
    saved: float = Field(0, ge=0)
    deadline: Optional[date] = None


class AmountIn(BaseModel):
    amount: float = Field(gt=0)


def goal_out(g: Goal) -> dict:
    return {"id": g.id, "name": g.name, "target": g.target_minor / 100, "saved": g.saved_minor / 100,
            "pct": min(100, round(g.saved_minor / g.target_minor * 100, 1)), "deadline": g.deadline.isoformat() if g.deadline else None}


@api.get("/goals")
def get_goals(u: User = Depends(current_user), db: Session = Depends(get_db)):
    return [goal_out(g) for g in db.query(Goal).filter(Goal.user_id == u.id).order_by(Goal.id)]


@api.post("/goals", status_code=201)
def add_goal(body: GoalIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    g = Goal(user_id=u.id, name=body.name, target_minor=minor(body.target), saved_minor=minor(body.saved), deadline=body.deadline)
    db.add(g)
    db.commit()
    return goal_out(g)


@api.post("/goals/{gid}/contribute")
def contribute(gid: int, body: AmountIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    g = db.get(Goal, gid)
    if not g or g.user_id != u.id:
        raise HTTPException(404, "Goal not found")
    g.saved_minor += minor(body.amount)
    db.commit()
    return goal_out(g)


@api.delete("/goals/{gid}", status_code=204)
def delete_goal(gid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    g = db.get(Goal, gid)
    if not g or g.user_id != u.id:
        raise HTTPException(404, "Goal not found")
    db.delete(g)
    db.commit()
    return Response(status_code=204)


@api.get("/alerts")
def alerts(u: User = Depends(current_user), db: Session = Depends(get_db)):
    out = []
    today = db.query(Expense).filter(Expense.user_id == u.id, Expense.date == date.today()).all()
    if today:
        out.append({"type": "expense", "text": f"You spent {sum(e.amount_minor for e in today) / 100:,.0f} {u.currency} today."})
    for b in A.budget_status(db, u.id, A.this_month()):
        if b["level"] == "exceeded":
            out.append({"type": "budget", "text": f"You crossed your {b['category']} limit ({b['pct']:.0f}% used)."})
        elif b["level"] == "warning":
            out.append({"type": "budget", "text": f"Warning: you have used {b['pct']:.0f}% of your {b['category']} budget."})
    for g in db.query(Goal).filter(Goal.user_id == u.id):
        if g.saved_minor < g.target_minor and g.deadline and g.deadline >= date.today():
            weeks = max(1, (g.deadline - date.today()).days // 7)
            out.append({"type": "goal", "text": f"Save about {(g.target_minor - g.saved_minor) / 100 / weeks:,.0f} {u.currency} per week to reach '{g.name}' by {g.deadline}."})
    return out


# ---------------- Dashboard & reports ----------------
@api.get("/dashboard")
def dashboard(month: Optional[str] = None, u: User = Depends(current_user), db: Session = Depends(get_db)):
    month = check_month(month)
    s, e = A.month_bounds(month)
    first, _ = A.month_bounds(A.shift_month(month, -5))
    rows = db.query(Expense).filter(Expense.user_id == u.id, Expense.date >= first, Expense.date < e).all()
    monthly, daily, by_cat = defaultdict(int), defaultdict(int), defaultdict(int)
    for x in rows:
        monthly[x.date.strftime("%Y-%m")] += x.amount_minor
        if x.date >= s:
            daily[x.date.isoformat()] += x.amount_minor
            by_cat[x.category.name if x.category else "Uncategorized"] += x.amount_minor
    total = sum(by_cat.values())
    return {"month": month, "income": u.monthly_income_minor / 100, "expense": total / 100,
            "savings": (u.monthly_income_minor - total) / 100, "currency": u.currency,
            "by_category": {k: v / 100 for k, v in sorted(by_cat.items(), key=lambda kv: -kv[1])},
            "prev_by_category": {k: v / 100 for k, v in A.spent_by_category(db, u.id, A.shift_month(month, -1)).items()},
            "monthly": [{"month": m, "total": monthly.get(m, 0) / 100} for m in (A.shift_month(month, -i) for i in range(5, -1, -1))],
            "daily": [{"date": d, "total": v / 100} for d, v in sorted(daily.items())], "budgets": A.budget_status(db, u.id, month)}


@api.get("/reports/monthly")
def monthly_report(month: Optional[str] = None, format: str = Query("pdf", pattern="^(pdf|xlsx)$"),
                   u: User = Depends(current_user), db: Session = Depends(get_db)):
    month = check_month(month)
    s, e = A.month_bounds(month)
    exps = [ex_out(x) for x in db.query(Expense).filter(Expense.user_id == u.id, Expense.date >= s, Expense.date < e).order_by(Expense.date)]
    by_cat = {k: v / 100 for k, v in A.spent_by_category(db, u.id, month).items()}
    if format == "pdf":
        return Response(reports.monthly_pdf(u, month, exps, by_cat), media_type="application/pdf",
                        headers={"Content-Disposition": f"attachment; filename=report-{month}.pdf"})
    return Response(reports.monthly_xlsx(u, month, exps, by_cat), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f"attachment; filename=report-{month}.xlsx"})


@app.get("/health")
def health():
    return {"status": "ok", "llm_configured": llm.available()}


app.include_router(api)
app.include_router(extras_router)

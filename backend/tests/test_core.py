import os, tempfile
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/t.db"
from fastapi.testclient import TestClient
from app.main import app
from app.services import nlp, analytics as A
from app.services.ocr import parse_receipt_text

client = TestClient(app)


def test_rule_parsing():
    r = nlp.parse_rules("Bought KFC dinner 500 taka")
    assert (r["amount"], r["currency"], r["category"], r["subcategory"]) == (500.0, "BDT", "Food", "Restaurant")
    assert nlp.parse_rules("I paid Uber 300 taka")["category"] == "Transportation"
    assert nlp.parse_rules("Paid $25 for medicine")["currency"] == "USD"


def test_receipt_parsing():
    r = parse_receipt_text("Shwapno Super Shop\nRice 500\nMilk 120\nTotal 620\n07/10/2026")
    assert r["amount"] == 620 and r["date"] == "2026-10-07" and r["store"].startswith("Shwapno")


def test_forecast_picks_a_method_and_is_nonnegative():
    r = A.forecast_series([100, 110, 120, 130, 140, 150])
    assert r["method"] in ("naive", "moving_average", "linear_regression") and r["prediction"] >= 0
    assert A.forecast_series([100, 200])["prediction"] >= 0


def test_full_flow_and_user_isolation():
    t = client.post("/api/auth/register", json={"name": "A", "email": "a@x.com", "password": "password1"}).json()["token"]
    h = {"Authorization": f"Bearer {t}"}
    assert client.get("/api/expenses").status_code == 401
    cats = client.get("/api/categories", headers=h).json()
    food = next(c for c in cats if c["name"] == "Food")["id"]
    ex = client.post("/api/expenses", headers=h, json={"amount": 25.5, "date": "2026-10-07", "category_id": food, "description": "Dinner"})
    assert ex.status_code == 201 and ex.json()["amount"] == 25.5
    p = client.post("/api/ai/parse-expense", headers=h, json={"text": "uber 300 taka"}).json()
    assert p["category"] == "Transportation"
    client.put("/api/budgets", headers=h, json={"category_id": food, "month": A.this_month(), "limit": 100})
    assert client.get("/api/dashboard", headers=h).status_code == 200
    assert client.get("/api/reports/monthly?format=xlsx", headers=h).status_code == 200
    assert client.get("/api/reports/monthly?format=pdf", headers=h).headers["content-type"] == "application/pdf"
    # second user cannot see or touch first user's data
    t2 = client.post("/api/auth/register", json={"name": "B", "email": "b@x.com", "password": "password2"}).json()["token"]
    h2 = {"Authorization": f"Bearer {t2}"}
    assert client.get("/api/expenses", headers=h2).json() == []
    assert client.delete(f"/api/expenses/{ex.json()['id']}", headers=h2).status_code == 404


def test_extras_flow():
    t = client.post("/api/auth/register", json={"name": "C", "email": "c@x.com", "password": "password3"}).json()["token"]
    h = {"Authorization": f"Bearer {t}"}
    client.put("/api/me", headers=h, json={"monthly_income": 50000})
    assert 0 <= client.get("/api/health-score", headers=h).json()["score"] <= 100
    assert client.get("/api/story", headers=h).json()["lines"]
    assert client.get("/api/wrapped", headers=h).status_code == 200
    assert client.get("/api/notifications", headers=h).json()
    ch = client.post("/api/challenges", headers=h, json={"daily": 100}).json()
    r = client.post(f"/api/challenges/{ch['id']}/checkin", headers=h).json()
    assert r["done_days"] == 1 and r["checked_today"] and r["saved"] == 100
    assert client.post(f"/api/challenges/{ch['id']}/checkin", headers=h).json()["done_days"] == 1  # idempotent
    a = client.post("/api/ai/chat", headers=h, json={"question": "Can I buy an iPhone this month?"}).json()
    assert "iPhone" not in a["answer"] or a["answer"]  # answered
    assert "130,000" in a["answer"]

"""Create a demo user with ~6 months of realistic expenses:  python seed.py"""
import random
from datetime import date, timedelta
from app.db import SessionLocal, User, Expense, Category, Budget, Goal, Challenge
from app.main import create_user
from app.services import analytics as A

random.seed(7)
PROFILE = {  # category: (avg count/month, (min, max) amount in BDT, descriptions)
    "Food": (22, (150, 900), ["KFC dinner", "Lunch at office", "Foodpanda order", "Shwapno groceries", "Coffee"]),
    "Transportation": (18, (50, 450), ["Uber ride", "Pathao", "Bus fare", "CNG"]),
    "Shopping": (5, (800, 3500), ["Daraz order", "Shirt", "Shoes", "Gift"]),
    "Entertainment": (4, (200, 900), ["Netflix", "Movie night", "Spotify"]),
    "Healthcare": (2, (300, 1500), ["Pharmacy", "Doctor visit"]),
    "Education": (2, (500, 2500), ["Udemy course", "Books"]),
    "Bills": (3, (800, 2500), ["Internet bill", "Electricity", "Mobile recharge"]),
    "Rent": (1, (14000, 14000), ["House rent"]),
}
db = SessionLocal()
u = db.query(User).filter(User.email == "demo@example.com").first()
if u:
    db.query(Expense).filter(Expense.user_id == u.id).delete()
    db.query(Budget).filter(Budget.user_id == u.id).delete()
    db.query(Goal).filter(Goal.user_id == u.id).delete()
    db.query(Challenge).filter(Challenge.user_id == u.id).delete()
else:
    u = create_user(db, "Demo User", "demo@example.com", "demo1234", income=60000)
u.monthly_income_minor, u.financial_goals = 6000000, "Buy a laptop, build an emergency fund"
cats = {c.name: c.id for c in db.query(Category).filter(Category.user_id == u.id)}
today = date.today()
for back in range(6, -1, -1):
    m = A.shift_month(A.this_month(), -back)
    s, e = A.month_bounds(m)
    last_day = min(e - timedelta(days=1), today)
    days = (last_day - s).days + 1
    growth = 1 + (6 - back) * 0.03  # gentle upward trend
    for name, (n, (lo, hi), descs) in PROFILE.items():
        count = max(1, round(n * (days / 30)))
        for _ in range(count):
            d = s + timedelta(days=random.randrange(days) if name != "Rent" else 0)
            amt = round(random.uniform(lo, hi) * (growth if name in ("Food", "Shopping") else 1), 2)
            db.add(Expense(user_id=u.id, category_id=cats[name], amount_minor=int(amt * 100), date=d,
                           payment_method=random.choice(["cash", "card", "bkash"]), description=random.choice(descs)))
for name, lim in {"Food": 12000, "Transportation": 5000, "Shopping": 8000, "Entertainment": 3000}.items():
    db.add(Budget(user_id=u.id, category_id=cats[name], month=A.this_month(), limit_minor=lim * 100))
db.add(Goal(user_id=u.id, name="Buy a laptop", target_minor=10000000, saved_minor=4000000, deadline=today + timedelta(days=150)))
db.add(Challenge(user_id=u.id, name="30-Day Saving Challenge", days=30, daily_minor=30000, start_date=today - timedelta(days=11), checkins=",".join(str(i) for i in range(1, 12))))
db.commit()
print("Seeded demo@example.com / demo1234")

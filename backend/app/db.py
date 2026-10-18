import os
from datetime import date
from sqlalchemy import create_engine, ForeignKey, String, Integer, Date, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'expense.db')}"
print(f"[expense-tracker] database: {DATABASE_URL}")
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite:") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    pass


# Money is always stored as integer minor units (paisa/cents) -- never floats.
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    monthly_income_minor: Mapped[int] = mapped_column(Integer, default=0)
    currency: Mapped[str] = mapped_column(String(8), default="BDT")
    financial_goals: Mapped[str] = mapped_column(Text, default="")
    budget_preference: Mapped[str] = mapped_column(String(32), default="balanced")


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("user_id", "name"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(60))
    is_default: Mapped[bool] = mapped_column(default=False)


class Expense(Base):
    __tablename__ = "expenses"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    amount_minor: Mapped[int] = mapped_column(Integer)
    date: Mapped[date] = mapped_column(Date, index=True)
    subcategory: Mapped[str | None] = mapped_column(String(60), nullable=True)
    payment_method: Mapped[str] = mapped_column(String(30), default="cash")
    description: Mapped[str] = mapped_column(String(255), default="")
    receipt_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[Category | None] = relationship()


class Budget(Base):
    __tablename__ = "budgets"
    __table_args__ = (UniqueConstraint("user_id", "category_id", "month"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    month: Mapped[str] = mapped_column(String(7))  # YYYY-MM
    limit_minor: Mapped[int] = mapped_column(Integer)
    category: Mapped[Category] = relationship()


class Goal(Base):
    __tablename__ = "goals"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    target_minor: Mapped[int] = mapped_column(Integer)
    saved_minor: Mapped[int] = mapped_column(Integer, default=0)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class Challenge(Base):
    __tablename__ = "challenges"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    days: Mapped[int] = mapped_column(Integer, default=30)
    daily_minor: Mapped[int] = mapped_column(Integer)
    start_date: Mapped[date] = mapped_column(Date)
    checkins: Mapped[str] = mapped_column(Text, default="")  # comma-separated day numbers

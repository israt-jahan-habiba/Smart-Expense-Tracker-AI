# Smart Expense Tracker AI: your personal AI financial companion

Track expenses, set budgets, and get insights and forecasts computed from your own data.
Animated glassmorphism UI (dark/light), Framer Motion, voice input, gamification.
Stack: **FastAPI + SQLAlchemy** (SQLite by default, PostgreSQL supported), **React + Vite + Chart.js**, scikit-learn, Tesseract OCR, optional LLM (Anthropic or OpenAI).

## Quick start

```bash
# 1. Backend (Python 3.10+)
cd backend
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                  # optional: set SECRET_KEY / API keys
python seed.py                                        # demo user + 6 months of data
uvicorn app.main:app --reload                         # http://localhost:8000/docs

# 2. Frontend (Node 18+), in a second terminal
cd frontend
npm install
npm run dev                                           # http://localhost:5173
```

Demo login (after `seed.py`): `demo@example.com` / `demo1234`.
API docs are auto-generated at `http://localhost:8000/docs`. Run tests with `cd backend && pytest`.

Load `.env` values with `export $(grep -v '^#' .env | xargs)` (or `set -a; source .env; set +a`) before starting uvicorn.

### Optional pieces
- **LLM features**: set `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`. Without a key, expense parsing uses keyword rules and the advisor returns rule-based answers.
- **Receipt OCR**: RapidOCR is in `requirements.txt` and also installs itself automatically on the first receipt scan (set `OCR_AUTO_INSTALL=0` to disable). Tesseract also works if installed (`sudo apt install tesseract-ocr`, `brew install tesseract`, or the Windows installer; set `TESSERACT_CMD` if it is not found). The app tries RapidOCR first, then Tesseract. OCR can misread digits, so always check the filled-in form before saving.
- **PostgreSQL**: `docker compose up -d`, then set `DATABASE_URL=postgresql+psycopg2://expense:expense@localhost:5432/expense`.

## Where your data is stored
SQLite data lives in one fixed file, `backend/expense.db`, no matter which folder you start the server from (the startup log prints the exact path). To reset everything, stop the server and delete that file. Back it up by copying it. Use PostgreSQL (`DATABASE_URL`) if the app runs somewhere that wipes files on restart.

## Interactive features (v2)
| Feature | Where |
|---|---|
| Animated 3-screen onboarding (income, saving goal, priorities) | `src/Onboarding.jsx` (shown to new users with no income set) |
| Counting numbers, filling progress rings, Financial Health Score + avatar | `src/components.jsx`, `Dashboard.jsx`, `/api/health-score` |
| Interactive spending wheel with month-over-month detail | `src/Wheel.jsx` |
| AI chatbot with voice input and "Can I buy X?" affordability check | `pages/Insights.jsx`, `app/extras.py: purchase_check` |
| Floating + button, animated category picker, voice entry, receipt scan laser | `src/EntryModal.jsx` |
| Money Story and Monthly Wrapped (auto-advancing story slides) | `src/Wrapped.jsx`, `/api/story`, `/api/wrapped` |
| Saving challenges, streaks and badges | `pages/Challenges.jsx`, `/api/challenges` |
| Smart, friendly notifications tied to your goals | `/api/notifications` |
| Goal progress bars with confetti on completion | `pages/Budgets.jsx` |
| Animated forecast bars with trend arrows | `pages/Insights.jsx` |

Notes: voice input uses the browser Web Speech API (Chrome/Edge; it is disabled elsewhere). Animations respect the OS "reduce motion" setting.
Lottie, Three.js and Next.js from the wishlist were swapped for lighter equivalents (animated SVG, an SVG wheel, Vite) to keep it simple to run.
The health score weights savings rate 40%, budget control 30%, steady spending 30%. Debt management is not scored because the app does not track debt.

## Feature map (v1)

| Spec feature | Where it lives |
|---|---|
| Auth, JWT, bcrypt, profile | `app/security.py`, `/api/auth/*`, `/api/me` |
| Expense CRUD, custom categories, search/filter | `/api/expenses`, `/api/categories` |
| AI categorization from text | `services/nlp.py` (LLM -> JSON validation -> rule fallback) |
| Receipt OCR | `services/ocr.py` (OpenCV preprocessing + Tesseract; user confirms before saving) |
| Dashboard charts | `/api/dashboard`, `frontend/src/pages/Dashboard.jsx` |
| Budgets and alerts | `/api/budgets`, `/api/alerts` |
| Spending insights | `services/analytics.py: insights()` (computed in code, never by the LLM) |
| AI advisor chatbot | `/api/ai/chat`: LLM sees only computed facts; rule-based fallback |
| Expense forecast | `analytics.forecast_series()`: naive / 3-month average / linear regression, best chosen by walk-forward backtest MAE |
| Saving goals | `/api/goals` |
| PDF / Excel reports | `/api/reports/monthly?format=pdf|xlsx` |

## Design decisions worth explaining in an interview
1. **Insights are computed, then explained.** The LLM never analyzes raw data, so it cannot invent numbers.
2. **Simple forecasting.** With a few months per user, LSTM would overfit. Each category picks the method with the lowest back-test error, and the UI shows that error.
3. **OCR is assistive.** Extracted values land in an editable form; nothing is saved without confirmation.
4. **Money is stored as integer minor units** (paisa/cents), never floats.
5. **Failure handling.** Bad LLM JSON, a missing API key, or an API outage all fall back to rules; the app keeps working.
6. **Per-user scoping.** Every query filters by `user_id`; a test verifies one user cannot read or delete another's data.

## Not included (future work)
Subscription tracker, RAG over financial documents, LSTM forecasting, push/email notifications (alerts are shown in-app), automated database backups, and a labeled accuracy test set for categorization (recommended: ~100 labeled entries).

## Security notes
Set a long random `SECRET_KEY` in production, serve over HTTPS, restrict `CORS_ORIGINS`, and move JWT storage from `localStorage` to httpOnly cookies for a hardened deployment.

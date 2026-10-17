<div align="center">

# Smart Expense Tracker AI

**Your personal AI-powered financial companion**

Track expenses, manage budgets, set savings goals, scan receipts, and get personalized financial insights and forecasts from your own data.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-Frontend-61DAFB?logo=react&logoColor=black)
![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?logo=sqlite&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-ML-F7931E?logo=scikitlearn&logoColor=white)

[Features](#features) · [Getting Started](#getting-started) · [How It Works](#how-it-works) · [Tech Stack](#tech-stack) · [Design Decisions](#design-decisions) · [Roadmap](#roadmap)

</div>

---

## Why I Built This

Most expense trackers only record transactions. **Smart Expense Tracker AI** goes further by combining expense management, budgeting, forecasting, OCR, financial health scoring, and AI-assisted guidance in one platform.

The goal is to help users understand their spending behavior, make better financial decisions, and interact with their personal finance data in a simple and engaging way.

## Live Demo

🔗 **Live demo:** _Coming soon_

## Features

| | Feature | Details |
|---|---|---|
| 💳 | **Expense Tracking** | Add, edit, delete, search, and filter expenses |
| 🧠 | **AI Categorization** | Categorizes expenses using LLM-assisted parsing with rule-based fallback |
| 📷 | **Receipt OCR** | Extracts receipt information using OpenCV and Tesseract |
| 📊 | **Dashboard Analytics** | Visualizes spending, trends, category breakdowns, and financial health |
| 💰 | **Budgets** | Create category budgets and receive alerts when spending approaches limits |
| 🎯 | **Saving Goals** | Track savings progress with animated progress indicators |
| 🔮 | **Expense Forecasting** | Predicts future spending using multiple forecasting methods |
| 🤖 | **AI Financial Advisor** | Provides financial guidance using computed user data rather than raw transactions |
| 🛒 | **Affordability Check** | Answers questions such as “Can I buy this?” based on current finances |
| 🔔 | **Smart Notifications** | Provides goal-aware and spending-aware notifications |
| 🏆 | **Challenges & Badges** | Gamified savings challenges, streaks, and achievements |
| 📖 | **Money Story** | Generates story-style summaries of financial activity |
| 📅 | **Monthly Wrapped** | Creates an interactive monthly financial recap |
| 📄 | **Reports** | Generates monthly PDF and Excel reports |
| 🌙 | **Responsive UI** | Animated glassmorphism interface with dark and light modes |
| 🎙️ | **Voice Input** | Supports browser-based voice expense entry |

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- npm

Optional:

- Tesseract OCR
- PostgreSQL
- OpenAI API key
- Anthropic API key

---

### Backend Setup

```bash
cd backend

python -m venv .venv
```

Activate the virtual environment.

**Windows**

```bash
.venv\Scripts\activate
```

**macOS / Linux**

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create the environment file:

```bash
cp .env.example .env
```

On Windows, you can manually copy `.env.example` and rename it to `.env`.

Seed demo data:

```bash
python seed.py
```

Start the backend:

```bash
uvicorn app.main:app --reload
```

API documentation:

```text
http://localhost:8000/docs
```

---

### Frontend Setup

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

---

### Demo Account

After running `seed.py`:

```text
Email: demo@example.com
Password: demo1234
```

---

### Run Tests

```bash
cd backend
pytest
```

## Optional Configuration

### AI / LLM Features

Set either:

```text
OPENAI_API_KEY
```

or:

```text
ANTHROPIC_API_KEY
```

If no API key is configured:

- Expense parsing falls back to keyword-based rules
- The financial advisor falls back to rule-based responses
- Core application features continue working

---

### Receipt OCR

Install Tesseract.

**Ubuntu / Debian**

```bash
sudo apt install tesseract-ocr
```

**macOS**

```bash
brew install tesseract
```

On Windows, install the Tesseract binary separately.

If Tesseract is unavailable, the receipt endpoint returns a clear `501` response instead of breaking the application.

---

### PostgreSQL

Start PostgreSQL using Docker:

```bash
docker compose up -d
```

Then configure:

```text
DATABASE_URL=postgresql+psycopg2://expense:expense@localhost:5432/expense
```

SQLite remains the default database.

## Interactive Features

### Onboarding

New users are guided through a three-screen onboarding flow covering:

- Income
- Saving goals
- Financial priorities

Location:

```text
frontend/src/Onboarding.jsx
```

### Financial Health Score

The system calculates a financial health score using:

- Savings rate: **40%**
- Budget control: **30%**
- Spending stability: **30%**

Debt management is not included because the application currently does not track debt.

### Spending Wheel

An interactive spending visualization displays category-level spending and month-over-month detail.

Location:

```text
frontend/src/Wheel.jsx
```

### AI Chatbot

The AI advisor supports:

- Natural-language financial questions
- Voice input
- Purchase affordability checks
- Rule-based fallback when an LLM is unavailable

### Expense Entry

The floating expense-entry interface includes:

- Animated category selection
- Voice input
- Receipt scanning
- Manual editing before saving OCR results

### Money Story & Monthly Wrapped

The application creates interactive story-style summaries of:

- Spending
- Savings
- Goals
- Monthly trends
- Financial achievements

### Challenges & Gamification

Users can participate in:

- Savings challenges
- Streaks
- Achievement badges
- Goal completion celebrations

## How It Works

### 1. Expense Management

Users create and manage transactions through authenticated API endpoints.

Every expense is scoped to the authenticated user.

### 2. AI Categorization

Expense text is processed using:

1. LLM-based categorization when configured
2. JSON validation
3. Rule-based fallback if the LLM fails or is unavailable

This ensures that expense entry continues working even when external AI services are unavailable.

### 3. Analytics

Financial insights are computed directly from user data in application code.

The LLM does **not** calculate financial numbers.

Instead:

1. The application computes facts and metrics
2. The AI layer receives those computed facts
3. The AI explains them in natural language

This reduces the risk of fabricated financial values.

### 4. Forecasting

The system compares multiple forecasting methods:

- Naive forecast
- Three-month moving average
- Linear regression

Each method is evaluated using walk-forward backtesting.

The model with the lowest MAE is selected.

### 5. Receipt Processing

Receipt OCR uses:

- OpenCV preprocessing
- Tesseract OCR
- User confirmation before saving

OCR output is always editable.

### 6. Financial Advisor

The advisor can answer questions using calculated financial facts, including affordability checks and spending insights.

## Project Structure

```text
Smart-Expense-Tracker-AI
├── backend/
│   ├── app/
│   │   ├── services/
│   │   ├── security.py
│   │   ├── extras.py
│   │   └── main.py
│   ├── tests/
│   ├── requirements.txt
│   └── seed.py
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   ├── components.jsx
│   │   ├── EntryModal.jsx
│   │   ├── Onboarding.jsx
│   │   ├── Wheel.jsx
│   │   └── Wrapped.jsx
│   ├── package.json
│   └── vite.config.js
│
├── docker-compose.yml
├── .gitignore
└── README.md
```

## API Highlights

| Feature | Endpoint / Module |
|---|---|
| Authentication | `/api/auth/*` |
| User profile | `/api/me` |
| Expenses | `/api/expenses` |
| Categories | `/api/categories` |
| Dashboard | `/api/dashboard` |
| Budgets | `/api/budgets` |
| Alerts | `/api/alerts` |
| Saving goals | `/api/goals` |
| Health score | `/api/health-score` |
| AI advisor | `/api/ai/chat` |
| Challenges | `/api/challenges` |
| Notifications | `/api/notifications` |
| Money story | `/api/story` |
| Monthly wrapped | `/api/wrapped` |
| Reports | `/api/reports/monthly?format=pdf|xlsx` |

## Tech Stack

### Backend
- Python
- FastAPI
- SQLAlchemy
- JWT authentication
- bcrypt
- SQLite / PostgreSQL

### Frontend
- React
- Vite
- Chart.js
- Framer Motion
- Web Speech API

### AI & Data
- scikit-learn
- OpenAI API — optional
- Anthropic API — optional
- Rule-based NLP fallback

### OCR
- OpenCV
- Tesseract OCR

### Reports
- PDF generation
- Excel generation

### Testing
- pytest

## Design Decisions

### 1. Insights Are Computed, Then Explained

The LLM does not analyze raw financial data or calculate totals.

Financial metrics are calculated in code first, then passed to the AI for explanation.

This helps prevent fabricated numbers.

### 2. Simple Forecasting Over Deep Learning

The application intentionally avoids LSTM forecasting.

With only a few months of data per user, a complex deep-learning model would likely overfit.

Instead, the system compares simpler forecasting methods and selects the one with the lowest backtest error.

### 3. OCR Is Assistive

Receipt OCR never automatically creates a transaction.

Extracted information is shown in an editable form and must be confirmed by the user.

### 4. Money Uses Integer Minor Units

Financial values are stored as integer minor units such as cents or paisa rather than floating-point values.

This avoids common floating-point precision errors.

### 5. Graceful AI Failure Handling

The application remains functional when:

- An AI API key is missing
- An AI provider is unavailable
- The model returns invalid JSON
- OCR is unavailable

Rule-based alternatives are used wherever possible.

### 6. Per-User Data Isolation

Every protected database query is scoped by `user_id`.

Tests verify that one user cannot access or delete another user's financial data.

## Security

For production deployments:

- Use a long random `SECRET_KEY`
- Serve the application over HTTPS
- Restrict `CORS_ORIGINS`
- Use PostgreSQL instead of local SQLite
- Move JWT storage from `localStorage` to secure `httpOnly` cookies
- Protect API credentials using environment variables
- Add automated database backups

## Project Highlights

- Built a full-stack AI-powered personal finance application using FastAPI and React.
- Implemented secure expense tracking, budgets, goals, dashboards, and financial reports.
- Developed a forecasting system that automatically selects the best-performing model using backtesting.
- Integrated OCR-assisted receipt scanning with editable confirmation.
- Designed an AI financial advisor that receives computed facts instead of raw financial data.
- Added voice input, gamification, challenges, financial health scoring, and monthly financial stories.
- Implemented graceful fallbacks so core functionality remains available without external AI services.

## Roadmap

### Completed

- Expense CRUD
- Authentication and user profiles
- Custom categories
- Search and filtering
- AI-assisted categorization
- Receipt OCR
- Dashboard analytics
- Budgets and alerts
- Financial health score
- Spending insights
- AI advisor
- Expense forecasting
- Saving goals
- Challenges and badges
- Voice input
- Monthly Wrapped
- Money Story
- PDF reports
- Excel reports
- SQLite and PostgreSQL support

### Planned

- Subscription tracker
- Retrieval-Augmented Generation over financial documents
- Push notifications
- Email notifications
- Automated database backups
- Larger labeled categorization benchmark
- Production deployment improvements

## Known Limitations

- Voice input depends on browser Web Speech API support.
- Tesseract must be installed separately for OCR.
- LLM features require an OpenAI or Anthropic API key.
- Debt is not currently tracked or included in the financial health score.
- SQLite is intended mainly for local development; PostgreSQL is recommended for production.

## Contributing

Issues, suggestions, and pull requests are welcome.

---

<div align="center">

Built by <strong><a href="https://github.com/israt-jahan-habiba">Israt Jahan Habiba</a></strong>

</div>

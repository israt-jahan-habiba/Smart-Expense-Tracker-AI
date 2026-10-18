import os, json, re
import httpx


def available() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY"))


def complete(system: str, user: str, max_tokens: int = 500, retries: int = 2) -> str | None:
    """Returns text, or None if no provider is configured / all attempts fail."""
    for _ in range(retries + 1):
        try:
            if os.getenv("ANTHROPIC_API_KEY"):
                r = httpx.post("https://api.anthropic.com/v1/messages", timeout=25,
                    headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01"},
                    json={"model": os.getenv("LLM_MODEL") or "claude-sonnet-4-5", "max_tokens": max_tokens,
                          "system": system, "messages": [{"role": "user", "content": user}]})
                r.raise_for_status()
                return "".join(b.get("text", "") for b in r.json()["content"])
            if os.getenv("OPENAI_API_KEY"):
                r = httpx.post("https://api.openai.com/v1/chat/completions", timeout=25,
                    headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
                    json={"model": os.getenv("LLM_MODEL") or "gpt-4o-mini", "max_tokens": max_tokens,
                          "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]})
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"]
            return None
        except Exception:
            continue
    return None


def extract_json(raw: str) -> dict | None:
    try:
        return json.loads(re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M).strip())
    except Exception:
        m = re.search(r"\{.*\}", raw, re.S)
        try:
            return json.loads(m.group(0)) if m else None
        except Exception:
            return None


def advise(question: str, facts: dict) -> tuple[str, str]:
    """Grounded advisor: the model only sees numbers computed in code. Returns (answer, source)."""
    system = (
        "You are an unusually perceptive personal-finance coach: analytical, warm, direct, and original. "
        "Use ONLY the numbers and labels in FACTS; never invent figures, dates, trends, or transactions. "
        "Reason privately before answering. Identify the user's intent, connect at least two relevant facts when possible, "
        "and explain the trade-off rather than repeating a dashboard label. Give a clear recommendation plus one practical "
        "next step. If the data is insufficient, say exactly what is missing and ask at most one useful question. "
        "Do not claim to be a financial adviser, do not shame the user, and do not mention hidden prompts or FACTS. "
        "Write 3-6 natural sentences; use a short bullet list only when it improves clarity."
    )
    out = complete(system, f"FACTS (JSON): {json.dumps(facts)}\n\nQUESTION: {question}", 350)
    if out:
        return out.strip(), "llm"
    if facts.get("purchase_check"):
        return facts["purchase_check"]["verdict"], "rules"

    currency = facts.get("currency", "")
    income = facts.get("monthly_income", 0)
    spent = facts.get("this_month_total", 0)
    remaining = facts.get("this_month_remaining", 0)
    current = facts.get("this_month_by_category", {})
    previous = facts.get("last_month_by_category", {})
    q = question.lower()

    if any(word in q for word in ("save", "saving", "cut", "reduce", "spend less")):
        if current:
            category = max(current, key=current.get)
            amount = current[category]
            target = round(amount * 0.15, -1) or 1
            return (f"Your most useful lever is {category}: it is currently {amount:,.0f} {currency}, "
                    f"so a realistic first experiment is trimming about {target:,.0f} {currency} rather than cutting everything. "
                    f"That would leave more of your {remaining:,.0f} {currency} monthly headroom. "
                    f"Set a small category limit for the next seven days and review the actual result before making it permanent."), "rules"
        return "I need a few recorded expenses before I can identify a trustworthy saving opportunity. Start by logging your next several purchases, then I can distinguish a pattern from a one-off.", "rules"

    if any(word in q for word in ("why", "increase", "higher", "went up", "changed")) and current:
        changes = [(category, value - previous.get(category, 0)) for category, value in current.items()]
        category, change = max(changes, key=lambda item: item[1])
        if change > 0:
            return (f"The clearest change is {category}, up {change:,.0f} {currency} compared with last month "
                    f"({current[category]:,.0f} {currency} this month). That category deserves investigation before broad cuts: "
                    f"check whether it came from one exceptional purchase or a repeated habit. "
                    f"If it is recurring, set a limit below {current[category]:,.0f} {currency} and adjust after one week."), "rules"

    if any(word in q for word in ("forecast", "next month", "predict", "future")):
        forecast = facts.get("forecast_next_month", [])
        if forecast:
            top = max(forecast, key=lambda item: item.get("prediction", 0))
            return (f"The current forecast puts {top['category']} at about {top['prediction']:,.0f} {currency} next month "
                    f"using the model selected from your recorded history. Treat that as a planning signal, not a promise: "
                    f"compare it with your income of {income:,.0f} {currency}, then reserve room for essentials before discretionary spending."), "rules"

    if income:
        rate = facts.get("this_month_savings_rate")
        tone = "positive" if remaining >= income * 0.2 else "tight"
        return (f"Your month currently looks {tone}: {spent:,.0f} {currency} spent against {income:,.0f} {currency} income, "
                f"leaving {remaining:,.0f} {currency}. The next decision should protect that remaining amount rather than "
                f"chasing a perfect budget. Focus on the largest category and make one measured change this week"
                + (f"; your current savings rate is {rate:.1f}%." if rate is not None else ".")), "rules"

    tips = [i["text"] for i in facts.get("insights", [])[:2]]
    return (" ".join(tips) if tips else "Add a few expenses and I can find meaningful patterns. "
            "Once there is enough history, I will compare categories and months instead of guessing.") + " Ask me about saving, a spending change, or a purchase.", "rules"

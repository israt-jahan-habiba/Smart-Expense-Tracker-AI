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
    system = ("You are a concise, practical personal-finance coach. Use ONLY the numbers in FACTS; never invent figures. "
              "If FACTS lack what is needed, say so. Give 2-4 sentences with concrete actions. Not professional financial advice.")
    out = complete(system, f"FACTS (JSON): {json.dumps(facts)}\n\nQUESTION: {question}", 350)
    if out:
        return out.strip(), "llm"
    if facts.get("purchase_check"):
        return facts["purchase_check"]["verdict"], "rules"
    tips = [i["text"] for i in facts.get("insights", [])[:3]] or ["Add a few more expenses so I can spot patterns."]
    return " ".join(tips) + " Tip: set a budget for your top category and review it weekly.", "rules"

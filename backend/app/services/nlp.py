"""Natural-language expense parsing: LLM first (if configured), rule-based fallback always available."""
import re
from datetime import date, timedelta
from . import llm

CATEGORIES = ["Food", "Transportation", "Shopping", "Entertainment", "Healthcare", "Education", "Bills", "Rent", "Other"]

KEYWORDS = {
    "Food": {
        "Restaurant": ["kfc", "pizza", "burger", "dinner", "lunch", "breakfast", "restaurant", "cafe", "coffee", "biryani", "foodpanda", "snack", "tea"],
        "Grocery": ["shwapno", "grocery", "groceries", "rice", "milk", "agora", "meena", "vegetable", "vegetables", "fish", "egg", "eggs", "bazar"],
    },
    "Transportation": {
        "Ride": ["uber", "pathao", "obhai", "rickshaw", "cng", "taxi", "ride"],
        "Public": ["bus", "metro", "train", "ticket", "launch"],
        "Fuel": ["fuel", "petrol", "octane", "diesel"],
    },
    "Shopping": {"Retail": ["daraz", "shirt", "shoes", "clothes", "shopping", "amazon", "gift", "bag", "watch"]},
    "Entertainment": {"Leisure": ["netflix", "spotify", "movie", "cinema", "game", "concert", "youtube", "hoichoi"]},
    "Healthcare": {"Medical": ["medicine", "doctor", "pharmacy", "hospital", "clinic", "dental", "lab"]},
    "Education": {"Learning": ["tuition", "course", "book", "books", "udemy", "exam", "school", "coaching"]},
    "Bills": {"Utilities": ["electricity", "gas", "wifi", "internet", "water", "bill", "recharge", "grameenphone", "robi", "banglalink"]},
    "Rent": {"Housing": ["rent", "landlord"]},
}
CUR = {"taka": "BDT", "tk": "BDT", "bdt": "BDT", "৳": "BDT", "usd": "USD", "$": "USD", "dollar": "USD", "dollars": "USD"}
NUM = re.compile(r"(৳|\$)?\s*(\d[\d,]*(?:\.\d+)?)\s*(taka|tk|bdt|usd|dollars?|৳|\$)?", re.I)


def categorize(text: str) -> tuple[str, str | None]:
    for w in re.findall(r"[a-z]+", text.lower()):
        for cat, subs in KEYWORDS.items():
            for sub, kws in subs.items():
                if w in kws:
                    return cat, sub
    return "Other", None


def parse_rules(text: str, default_currency: str = "BDT") -> dict:
    best = None
    for m in NUM.finditer(text):
        pre, num, post = m.group(1), m.group(2), (m.group(3) or "").lower()
        marker = pre or post
        score = 2 if marker else 1
        if best is None or score > best[0]:
            best = (score, float(num.replace(",", "")), CUR.get(marker.lower(), default_currency) if marker else default_currency)
    if best is None:
        raise ValueError("No amount found in text")
    d = date.today()
    if "yesterday" in text.lower():
        d -= timedelta(days=1)
    cat, sub = categorize(text)
    return {"amount": best[1], "currency": best[2], "category": cat, "subcategory": sub,
            "description": text.strip()[:255], "date": d.isoformat(), "source": "rules"}


def _validate(obj: dict) -> dict:
    amount = float(obj["amount"])
    if amount <= 0:
        raise ValueError("amount must be positive")
    cat = obj.get("category") if obj.get("category") in CATEGORIES else "Other"
    d = str(obj.get("date") or date.today().isoformat())
    date.fromisoformat(d)  # raises if malformed
    return {"amount": amount, "currency": str(obj.get("currency") or "BDT").upper()[:3], "category": cat,
            "subcategory": obj.get("subcategory") or None, "description": str(obj.get("description") or "")[:255],
            "date": d, "source": "llm"}


def parse_expense(text: str, default_currency: str = "BDT") -> dict:
    if llm.available():
        prompt = (f"Today is {date.today().isoformat()}. Extract one expense from the text. Reply with ONLY a JSON object: "
                  f'{{"amount": number, "currency": "BDT|USD|...", "category": one of {CATEGORIES}, '
                  '"subcategory": short string, "description": short string, "date": "YYYY-MM-DD"}}. '
                  f"Default currency is {default_currency}.\nText: {text}")
        raw = llm.complete("You convert messy expense notes into strict JSON. No prose, no markdown.", prompt, 200)
        obj = llm.extract_json(raw) if raw else None
        if obj:
            try:
                return _validate(obj)
            except Exception:
                pass  # bad LLM output -> fall through to rules
    return parse_rules(text, default_currency)

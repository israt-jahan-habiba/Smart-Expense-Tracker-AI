"""Receipt OCR (assistive): extract store / total / date, user confirms before saving."""
import io, re
from datetime import date
from .nlp import categorize


def preprocess(img_bytes: bytes):
    from PIL import Image
    try:
        import cv2, numpy as np
        arr = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_GRAYSCALE)
        arr = cv2.resize(arr, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
        arr = cv2.adaptiveThreshold(arr, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15)
        return Image.fromarray(arr)
    except Exception:
        return Image.open(io.BytesIO(img_bytes)).convert("L")


def parse_receipt_text(text: str) -> dict:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    store = lines[0] if lines else ""
    total = None
    for l in lines:
        if re.search(r"total|grand|amount due", l, re.I) and not re.search(r"sub\s*total", l, re.I):
            nums = re.findall(r"\d[\d,]*\.?\d*", l)
            if nums:
                total = float(nums[-1].replace(",", ""))
    if total is None:  # fallback: largest number on the receipt
        nums = [float(n.replace(",", "")) for n in re.findall(r"\d[\d,]*\.?\d*", text) if n.replace(",", "").replace(".", "").isdigit()]
        total = max(nums) if nums else None
    m = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", text)
    d = date.today().isoformat()
    if m:
        dd, mm, yy = int(m[1]), int(m[2]), int(m[3])
        try:
            d = date(yy + 2000 if yy < 100 else yy, mm, dd).isoformat()
        except ValueError:
            pass
    cat, sub = categorize(text)
    return {"amount": total, "store": store, "category": cat, "subcategory": sub, "date": d, "description": store, "raw_text": text}


def scan(img_bytes: bytes) -> dict:
    import pytesseract  # requires the tesseract binary installed on the machine
    return parse_receipt_text(pytesseract.image_to_string(preprocess(img_bytes)))

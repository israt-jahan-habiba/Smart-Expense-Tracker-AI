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


class OCRUnavailable(Exception):
    pass


def _tesseract(img_bytes: bytes) -> str:
    import os, shutil
    import pytesseract
    cmd = os.getenv("TESSERACT_CMD") or shutil.which("tesseract")
    if not cmd:  # the Windows installer does not add itself to PATH
        for p in (r"C:\Program Files\Tesseract-OCR\tesseract.exe", r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                  "/opt/homebrew/bin/tesseract", "/usr/local/bin/tesseract", "/usr/bin/tesseract"):
            if os.path.exists(p):
                cmd = p
                break
    if not cmd:
        raise OCRUnavailable("Tesseract not found")
    pytesseract.pytesseract.tesseract_cmd = cmd
    return pytesseract.image_to_string(preprocess(img_bytes))


def _ensure_rapidocr():
    """Import RapidOCR; if missing, install it once into the Python that is running this server."""
    import os, subprocess, sys, importlib
    try:
        return importlib.import_module("rapidocr_onnxruntime")
    except ImportError:
        if os.getenv("OCR_AUTO_INSTALL", "1") != "1":
            raise
    r = subprocess.run([sys.executable, "-m", "pip", "install", "rapidocr-onnxruntime"], capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        raise OCRUnavailable("automatic install of rapidocr-onnxruntime failed: " + (r.stderr or r.stdout)[-300:])
    importlib.invalidate_caches()
    return importlib.import_module("rapidocr_onnxruntime")


def _rapidocr(img_bytes: bytes) -> str:
    """Pure-pip OCR engine (no separate program needed). Auto-installed on first use."""
    RapidOCR = _ensure_rapidocr().RapidOCR
    result, _ = RapidOCR()(img_bytes)
    if not result:
        return ""
    items = sorted(((b[0][1], b[0][0], t, abs(b[2][1] - b[0][1]) or 10) for b, t, _ in result))
    lines, cur, cy = [], [], None
    for y, x, t, h in items:
        if cy is not None and abs(y - cy) > 0.6 * h:
            lines.append(cur)
            cur = []
        if not cur:
            cy = y
        cur.append((x, t))
    if cur:
        lines.append(cur)
    return "\n".join(" ".join(t for _, t in sorted(l)) for l in lines)


def scan(img_bytes: bytes) -> dict:
    errors = []
    for engine in (_rapidocr, _tesseract):
        try:
            text = engine(img_bytes)
            if text.strip():
                return parse_receipt_text(text)
            errors.append(f"{engine.__name__}: no text found")
        except ImportError:
            errors.append(f"{engine.__name__}: not installed")
        except Exception as e:
            errors.append(f"{engine.__name__}: {e}")
    raise OCRUnavailable("; ".join(errors))

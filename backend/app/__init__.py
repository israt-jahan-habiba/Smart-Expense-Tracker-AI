"""Load backend/.env (if present) before anything reads environment variables."""
import os
from pathlib import Path

_env = Path(__file__).resolve().parent.parent / ".env"
if _env.exists():
    for _line in _env.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            if _v.strip():  # blank values in .env.example must not override real settings
                os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

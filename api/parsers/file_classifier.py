"""
Determines the type of each uploaded file before parsing.
"""
import io


def classify(filename: str, content_bytes: bytes) -> str:
    """
    Returns one of:
      products_csv       — Products Tab CSV
      search_terms_csv   — Search Terms Tab CSV
      image              — PNG/JPG screenshot (type refined inside image_parser)
      chrome_ext_txt     — Chrome Extension OEI export (.txt)
      ai_text_report     — AI-generated niche text report (.txt/.docx)
      unknown
    """
    name_lower = filename.lower()

    # ── Images ────────────────────────────────────────────────────────────────
    if name_lower.endswith((".png", ".jpg", ".jpeg", ".webp")):
        return "image"

    # ── CSV files ──────────────────────────────────────────────────────────────
    if name_lower.endswith(".csv"):
        try:
            text = content_bytes.decode("utf-8", errors="replace")
            lines = [l for l in text.splitlines() if l.strip()]
            for line in lines[:20]:
                lower = line.lower().lstrip("\ufeff")
                if "search term" in lower and any(k in lower for k in ("click share", "search volume", "total count", "growth", "conversion")):
                    return "search_terms_csv"
                if "asin" in lower and ("niche click count" in lower or "click share" in lower or "avg. best seller rank" in lower):
                    return "products_csv"
        except Exception:
            pass
        return "unknown"

    # ── Text files ─────────────────────────────────────────────────────────────
    if name_lower.endswith((".txt", ".docx")):
        try:
            if name_lower.endswith(".docx"):
                # Can't decode docx as text directly — treat as ai_text_report
                return "ai_text_report"
            text = content_bytes.decode("utf-8", errors="replace")
            # Chrome Extension export has both markers
            if "TOP NICHE INSIGHTS" in text and "MAIN NAVIGATION TABS" in text:
                return "chrome_ext_txt"
            # Standard AI text report
            if any(kw in text for kw in ["Niche Dynamics", "Niche Analysis", "TOP NICHE INSIGHTS"]):
                return "ai_text_report"
        except Exception:
            pass
        return "ai_text_report"  # default for txt

    return "unknown"


def _first_nonempty_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip().lstrip("\ufeff")  # strip BOM
        if stripped:
            return stripped
    return ""

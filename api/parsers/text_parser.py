"""
Text parser for:
  - Chrome Extension OEI export (.txt with TOP NICHE INSIGHTS + MAIN NAVIGATION TABS)
  - AI Text Report (.txt/.docx with Niche Dynamics / Niche Analysis)
"""
import io
import json
import re

import openai
import pandas as pd

from prompts.extraction import PROMPT_AI_TEXT_REPORT, PROMPT_CHROME_EXT_NARRATIVE

def _get_client(api_key: str):
    return openai.OpenAI(api_key=api_key)


def _extract_json(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return {}


def _call_claude_text(prompt: str, content: str, api_key: str) -> dict:
    client = _get_client(api_key)
    response = client.chat.completions.create(
        model="gpt-5.4",
        max_completion_tokens=2048,
        messages=[{"role": "user", "content": f"{prompt}\n\n---\n\n{content}"}],
    )
    return _extract_json(response.choices[0].message.content.strip())


def _pct_to_decimal(val) -> float:
    if val is None:
        return None
    try:
        s = str(val).replace(",", "").replace("%", "").replace("+", "").strip()
        if s in ("", "nan", "--"):
            return None
        f = float(s)
        if abs(f) > 2:
            return round(f / 100, 6)
        return round(f, 6)
    except (ValueError, TypeError):
        return None


def _to_int(val) -> int:
    if val is None:
        return None
    try:
        s = str(val).replace(",", "").replace("$", "").strip()
        return int(float(s))
    except (ValueError, TypeError):
        return None


def _to_float(val) -> float:
    if val is None:
        return None
    try:
        s = str(val).replace(",", "").replace("$", "").strip()
        return float(s)
    except (ValueError, TypeError):
        return None


# ── Chrome Extension TXT parser ───────────────────────────────────────────────

def _extract_section(text: str, heading: str) -> str:
    """Extract text between a heading and the next dashes separator."""
    pattern = rf"[-]{{30,}}\s*\n{re.escape(heading)}\s*\n[-]{{30,}}\n([\s\S]*?)(?=\n[-]{{30,}}|\Z)"
    match = re.search(pattern, text)
    return match.group(1).strip() if match else ""


def _parse_key_metrics(section: str) -> dict:
    """Parse KEY METRICS section into overview dict."""
    result = {}
    for line in section.splitlines():
        line = line.strip()
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip().lower()
        val = val.strip()
        if "productscount" in key or "productcount" in key or key == "productcount":
            result["num_top_clicked_products"] = _to_int(val.replace(",", ""))
        elif "searchvolume" in key or key == "searchvolume":
            result["search_volume_360d"] = _to_int(val.replace(",", ""))
        elif "searchvolumegrowth" in key:
            result["search_volume_growth_180d"] = _pct_to_decimal(val)
        elif "avgprice" in key or "averageprice" in key:
            result["avg_price_360d"] = _to_float(val.replace("$", ""))
        elif "unitssold" in key:
            result["units_sold_range"] = val
        elif "returnrate" in key:
            result["return_rate_360d"] = _pct_to_decimal(val)
    return result


def _parse_insights_trends(section: str) -> dict:
    """Parse INSIGHTS & TRENDS tab section."""
    result = {}
    lines = [l.strip() for l in section.splitlines() if l.strip()]
    for i, line in enumerate(lines):
        # Look for value on next line after metric name
        ll = line.lower()
        if "search volume" in ll and "growth" not in ll and i + 1 < len(lines):
            result["search_volume_360d"] = _to_int(lines[i + 1].replace(",", ""))
        elif "search volume growth" in ll and i + 1 < len(lines):
            result["search_volume_growth_180d"] = _pct_to_decimal(lines[i + 1])
        elif "# of top clicked" in ll and i + 1 < len(lines):
            result["num_top_clicked_products"] = _to_int(lines[i + 1])
        elif "average price" in ll and i + 1 < len(lines):
            result["avg_price_360d"] = _to_float(lines[i + 1].replace("$", ""))
        elif "range of average units" in ll and i + 2 < len(lines):
            lo = lines[i + 1].replace(",", "")
            hi = lines[i + 2].replace(",", "") if i + 2 < len(lines) else ""
            result["units_sold_range"] = f"{lo}-{hi}".strip("-")
        elif "return rate" in ll and i + 1 < len(lines):
            result["return_rate_360d"] = _pct_to_decimal(lines[i + 1])
    return result


def _parse_products_table(section: str) -> list:
    """Parse PRODUCTS tab table from Chrome Extension export."""
    lines = [l for l in section.splitlines() if l.strip()]
    # Find a line that looks like a TSV/pipe header
    header_idx = None
    for i, line in enumerate(lines):
        if "ASIN" in line or "asin" in line.lower():
            header_idx = i
            break
    if header_idx is None:
        return []

    # Try CSV parsing with tab separator
    table_text = "\n".join(lines[header_idx:])
    try:
        df = pd.read_csv(io.StringIO(table_text), sep="\t", dtype=str, on_bad_lines="skip")
    except Exception:
        try:
            df = pd.read_csv(io.StringIO(table_text), dtype=str, on_bad_lines="skip")
        except Exception:
            return []

    df.columns = [c.strip() for c in df.columns]
    products = []
    for _, row in df.iterrows():
        asin = str(row.get("ASIN", "")).strip()
        if not asin or asin in ("nan", ""):
            continue
        products.append({
            "asin": asin,
            "product_name": str(row.get("Product Name", "")).strip(),
            "brand": str(row.get("Brand", "")).strip(),
            "launch_date": str(row.get("Launch Date", "")).strip(),
            "click_count_360d": _to_int(row.get("Niche Click CountPast 360 days") or row.get("Niche Click Count")),
            "click_share_360d": _pct_to_decimal(row.get("Click SharePast 360 days") or row.get("Click Share")),
            "avg_price_360d": _to_float(str(row.get("Average Selling PricePast 360 days", "") or row.get("Average Selling Price", "")).replace("$", "")),
            "total_ratings": _to_int(row.get("Total RatingsPast 360 days") or row.get("Total Ratings")),
            "avg_rating": _to_float(str(row.get("Avg. Customer RatingPast 360 days", "") or row.get("Avg. Customer Rating", "")).replace("/5", "")),
            "avg_bsr": _to_int(row.get("Avg. Best Seller RankPast 360 days") or row.get("Avg. Best Seller Rank")),
            "avg_sellers_count": _to_int(row.get("Avg. # of Sellers & VendorsPast 360 days") or row.get("Avg. # of Sellers & Vendors")),
        })
    return products


def _parse_search_terms_table(section: str) -> list:
    """Parse SEARCH TERMS tab table from Chrome Extension export."""
    lines = [l for l in section.splitlines() if l.strip()]
    header_idx = None
    for i, line in enumerate(lines):
        if "Search Term" in line or "search term" in line.lower():
            header_idx = i
            break
    if header_idx is None:
        return []

    table_text = "\n".join(lines[header_idx:])
    try:
        df = pd.read_csv(io.StringIO(table_text), sep="\t", dtype=str, on_bad_lines="skip")
    except Exception:
        try:
            df = pd.read_csv(io.StringIO(table_text), dtype=str, on_bad_lines="skip")
        except Exception:
            return []

    df.columns = [c.strip() for c in df.columns]
    terms = []
    for _, row in df.iterrows():
        term = str(row.get("Search Term", "")).strip()
        if not term or term in ("nan", ""):
            continue
        # Find top product columns
        top_products = []
        for n, label in enumerate(["#1 Top Clicked Product", "#2 Top Clicked Product", "#3 Top Clicked Product"], start=1):
            # Try to find Product Name and ASIN columns for each
            for col in df.columns:
                cl = col.lower()
                if f"#{n}" in col or (f"top clicked" in cl and str(n) in cl):
                    if "asin" in cl:
                        asin = str(row.get(col, "")).strip()
                        if asin and asin != "nan":
                            # Find corresponding title
                            for c2 in df.columns:
                                if (f"#{n}" in c2 or (f"top clicked" in c2.lower() and str(n) in c2)) and "asin" not in c2.lower() and "image" not in c2.lower():
                                    title = str(row.get(c2, "")).strip()
                                    top_products.append({"rank": n, "title": title, "asin": asin})
                                    break

        terms.append({
            "term": term,
            "volume_360d": _to_int((row.get("Total CountPast 360 days") or row.get("Total Count", ""))),
            "growth_90d": _pct_to_decimal(row.get("GrowthPast 90 days") or row.get("Growth Past 90 days")),
            "growth_180d": _pct_to_decimal(row.get("GrowthPast 180 days") or row.get("Growth Past 180 days")),
            "click_share_360d": _pct_to_decimal(row.get("Click SharePast 360 days") or row.get("Click Share")),
            "conversion_rate_360d": _pct_to_decimal(row.get("Search ConversionPast 360 days") or row.get("Search Conversion")),
            "top_products": top_products,
        })
    return terms


def _parse_review_insights_table(section: str) -> list:
    """Parse CUSTOMER REVIEW INSIGHTS table."""
    topics = []
    current_topic = None
    current_rate = None
    subtopics = []

    for line in section.splitlines():
        line = line.strip()
        if not line or line.startswith("Topic") or line.startswith("Subtopic"):
            continue
        # Match percentage
        pct_match = re.search(r"(\d+\.\d+)%", line)
        if pct_match:
            pct = float(pct_match.group(1)) / 100
            # If line has no leading whitespace and it's a main topic
            topic_name = re.sub(r"\d+\.\d+%.*", "", line).strip()
            if topic_name:
                if current_topic:
                    topics.append({
                        "topic": current_topic,
                        "mention_rate": current_rate,
                        "subtopics": subtopics,
                    })
                current_topic = topic_name
                current_rate = pct
                subtopics = []
    if current_topic:
        topics.append({"topic": current_topic, "mention_rate": current_rate, "subtopics": subtopics})
    return topics


def _parse_returns_table(section: str) -> list:
    """Parse RETURNS table: Topic | %Mentions"""
    topics = []
    for line in section.splitlines():
        line = line.strip()
        if not line or "%" not in line or line.startswith("Topic"):
            continue
        pct_match = re.search(r"(\d+\.\d+)%", line)
        if pct_match:
            pct = float(pct_match.group(1)) / 100
            topic_name = re.sub(r"\d+\.\d+%.*", "", line).strip()
            if topic_name:
                severity = "critical" if pct >= 0.15 else "major" if pct >= 0.05 else "minor"
                topics.append({"topic": topic_name, "return_mention_rate": pct, "severity": severity})
    return topics


def parse_chrome_ext(content_bytes: bytes, api_key: str = "") -> dict:
    """Parse Chrome Extension OEI export file."""
    text = content_bytes.decode("utf-8", errors="replace")

    result = {
        "source_type": "chrome_ext_txt",
        "overview": {},
        "products": [],
        "search_terms": [],
        "review_topics_positive": [],
        "review_topics_negative": [],
        "return_topics": [],
        "ai_text": {},
    }

    # ── Extract structured sections ───────────────────────────────────────────

    # Niche overview from INSIGHTS & TRENDS tab
    insights_section = _extract_section(text, "INSIGHTS & TRENDS")
    if insights_section:
        result["overview"].update(_parse_insights_trends(insights_section))

    # Also try KEY METRICS section
    metrics_section = _extract_section(text, "KEY METRICS")
    if metrics_section:
        result["overview"].update(_parse_key_metrics(metrics_section))

    # Niche name from text
    niche_match = re.search(r"Niche:\s*(.+)", text)
    if niche_match:
        result["niche_name"] = niche_match.group(1).strip()

    # Products table
    products_section = _extract_section(text, "PRODUCTS")
    if products_section:
        result["products"] = _parse_products_table(products_section)

    # Search Terms table
    search_section = _extract_section(text, "SEARCH TERMS")
    if search_section:
        result["search_terms"] = _parse_search_terms_table(search_section)

    # Customer Review Insights
    review_section = _extract_section(text, "CUSTOMER REVIEW INSIGHTS")
    if review_section:
        result["review_topics_positive"] = _parse_review_insights_table(review_section)

    # Returns
    returns_section = _extract_section(text, "RETURNS")
    if returns_section:
        result["return_topics"] = _parse_returns_table(returns_section)

    # ── Extract narrative sections via Claude ─────────────────────────────────
    narrative_sections = []
    for heading in ["NICHE DYNAMICS", "CUSTOMER REVIEWS", "CUSTOMER DEMOGRAPHICS",
                    "SEARCH TERMS", "PRICING", "TOP PRODUCT FEATURES"]:
        sec = _extract_section(text, heading)
        if sec and len(sec) > 100:
            narrative_sections.append(f"=== {heading} ===\n{sec[:3000]}")

    if narrative_sections:
        narrative_text = "\n\n".join(narrative_sections)
        result["ai_text"] = _call_claude_text(PROMPT_CHROME_EXT_NARRATIVE, narrative_text, api_key)

    return result


# ── AI Text Report parser ─────────────────────────────────────────────────────

def parse_ai_text_report(content_bytes: bytes, api_key: str = "") -> dict:
    """Parse standalone AI text report (.txt or .docx)."""
    try:
        if hasattr(content_bytes, "read"):
            raw = content_bytes.read()
        else:
            raw = content_bytes
        text = raw.decode("utf-8", errors="replace")
    except Exception:
        text = str(content_bytes)

    # Limit to 8000 chars for Claude context efficiency
    truncated = text[:8000]
    return _call_claude_text(PROMPT_AI_TEXT_REPORT, truncated, api_key)

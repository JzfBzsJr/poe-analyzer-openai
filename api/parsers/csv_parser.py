"""
Deterministic CSV parser for POE Products Tab and Search Terms Tab.
Never uses Claude — pure pandas parsing.
"""
import io
import re
from datetime import datetime

import pandas as pd


# ── Product type classification ───────────────────────────────────────────────

_ADJACENT_KEYWORDS = [
    "jade roller", "gua sha", "ice roller", "eye massager", "eye mask",
    "derma roller", "microneedle", "hair brush", "shampoo brush", "scalp brush",
    "comb", "lip", "serum", "cream", "oil", "moisturizer", "primer", "sunscreen",
    "mask", "peel", "cleanser", "toner", "exfoliant", "loofah", "sponge",
    "makeup", "foundation", "concealer",
]
_UNRELATED_KEYWORDS = [
    "supplement", "vitamin", "collagen", "capsule", "tablet", "pill",
    "book", "course", "guide",
]


def _classify_product_type(name: str, niche_name: str = "") -> tuple:
    name_l = name.lower()
    for kw in _UNRELATED_KEYWORDS:
        if kw in name_l:
            return "unrelated", f"ДРУГОЙ ТИП ТОВАРА: {kw} — не является прямым конкурентом"
    for kw in _ADJACENT_KEYWORDS:
        if kw in name_l:
            return "adjacent", (
                f"ДРУГОЙ ТИП ТОВАРА: {kw} — появляется в результатах по запросу "
                f"'{niche_name}', но НЕ является прямым конкурентом"
            )
    return "direct", ""


def _months_since(launch_date_str) -> float:
    if not launch_date_str or str(launch_date_str) in ("nan", "NaT", "None", ""):
        return None
    for fmt in ("%m/%Y", "%Y-%m-%d", "%m/%d/%Y", "%Y-%m", "%m/%d/%y"):
        try:
            dt = datetime.strptime(str(launch_date_str).strip(), fmt)
            delta = (datetime.today() - dt).days / 30.44
            return max(delta, 1.0)
        except ValueError:
            continue
    return None


def _to_float(val):
    if val is None:
        return None
    try:
        s = str(val).replace(",", "").replace("%", "").replace("$", "").strip()
        if s in ("", "nan", "NaT", "None", "--"):
            return None
        return float(s)
    except (ValueError, TypeError):
        return None


def _to_int(val):
    f = _to_float(val)
    return int(f) if f is not None else None


def _pct_to_decimal(val):
    if val is None:
        return None
    try:
        s = str(val).replace(",", "").strip().lstrip("+")
        if s in ("", "nan", "--"):
            return None
        if "%" in s:
            return round(float(s.replace("%", "")) / 100, 6)
        f = float(s)
        if -2 < f < 2:
            return round(f, 6)
        return round(f / 100, 6)
    except (ValueError, TypeError):
        return None


def _is_spanish(term: str) -> bool:
    spanish_words = ["masajeador", "para la", "de cara", "cabeza", "facial para", "de cuero"]
    return any(w in term.lower() for w in spanish_words)


# ── Column name normalisation ─────────────────────────────────────────────────

def _col_map(columns) -> dict:
    """Build normalised key → actual column name mapping."""
    mapping = {}
    for c in columns:
        cl = c.lower().strip()
        # Search Terms CSV
        if cl == "search term":
            mapping["search_term"] = c
        elif ("total count" in cl) or ("search volume" in cl and "growth" not in cl):
            mapping.setdefault("volume", c)
        elif "growth" in cl and "90" in cl:
            mapping["growth_90d"] = c
        elif "growth" in cl and "180" in cl:
            mapping["growth_180d"] = c
        elif "search conversion" in cl or ("conversion rate" in cl and "search" not in cl):
            mapping.setdefault("conversion_rate", c)
        # Top clicked products (search terms CSV)
        elif ("#1" in cl or ("top clicked" in cl and "1" in cl and "2" not in cl and "3" not in cl)):
            if "asin" in cl:
                mapping["top_product_1_asin"] = c
            else:
                mapping.setdefault("top_product_1_title", c)
        elif "#2" in cl or ("top clicked" in cl and "2" in cl):
            if "asin" in cl:
                mapping["top_product_2_asin"] = c
            else:
                mapping.setdefault("top_product_2_title", c)
        elif "#3" in cl or ("top clicked" in cl and "3" in cl):
            if "asin" in cl:
                mapping["top_product_3_asin"] = c
            else:
                mapping.setdefault("top_product_3_title", c)
        # Products CSV
        elif cl in ("product name", "product title", "name"):
            mapping["product_name"] = c
        elif cl == "asin":
            mapping["asin"] = c
        elif cl == "brand":
            mapping["brand"] = c
        elif "category" in cl:
            mapping.setdefault("category", c)
        elif "launch date" in cl:
            mapping["launch_date"] = c
        elif "niche click count" in cl or "click count" in cl:
            mapping["click_count"] = c
        elif "click share" in cl and "top" not in cl:
            mapping.setdefault("click_share", c)
        elif ("average selling price" in cl or "avg. selling price" in cl
              or ("avg" in cl and "price" in cl and "selling" in cl)):
            mapping["avg_price"] = c
        elif "total ratings" in cl:
            mapping["total_ratings"] = c
        elif ("avg. customer rating" in cl or "avg customer rating" in cl
              or ("avg" in cl and "rating" in cl and "customer" in cl)):
            mapping["avg_rating"] = c
        elif ("avg. best seller rank" in cl or "avg best seller rank" in cl
              or "best seller rank" in cl):
            mapping["avg_bsr"] = c
        elif ("avg. # of sellers" in cl or "avg. number of sellers" in cl
              or ("sellers" in cl and "vendor" in cl)
              or ("# of sellers" in cl)):
            mapping["avg_sellers"] = c
    return mapping


def _v(row, col_map, key):
    actual = col_map.get(key)
    if actual is None:
        return None
    val = row.get(actual)
    if val is None or str(val) in ("nan", "NaT", "None", ""):
        return None
    return str(val).strip()


def _find_header_idx(lines, marker):
    for i, line in enumerate(lines):
        if marker.lower() in line.lower():
            return i
    return 0


# ── Search term clusters ──────────────────────────────────────────────────────

_CLUSTERS = {
    "general_massager": ["face massager", "facial massager", "face and neck massager",
                         "scalp massager", "head massager"],
    "lymphatic_drainage": ["lymphatic", "drainage", "contour face", "contouring"],
    "depuffing_sculpting": ["depuffer", "depuff", "puffiness", "sculptor", "sculpt", "slimming"],
    "red_light_led": ["red light", "led", "7 color", "light therapy"],
    "gua_sha_tools": ["gua sha", "jade roller", "ice roller", "roller"],
    "lifting_firming": ["lift", "lifting", "firming", "tightening", "anti-aging", "ems", "anti aging"],
    "hair_growth": ["hair growth", "scalp", "dandruff", "shampoo brush"],
    "scrubbing": ["scrubber", "scrubbing", "exfoliat"],
    "electric_device": ["electric", "cordless", "rechargeable", "wireless"],
    "spanish_language": ["masajeador", "para la cara", "de cara", "cabeza", "cuero cabelludo"],
    "device_generic": ["beauty device", "facial device", "face device"],
}


def _detect_cluster(term: str) -> str:
    t = term.lower()
    for cluster, keywords in _CLUSTERS.items():
        for kw in keywords:
            if kw in t:
                return cluster
    return "other"


def _detect_momentum(growth_180d) -> str:
    if growth_180d is None:
        return "unknown"
    if growth_180d > 1.0:
        return "exploding"
    if growth_180d > 0.2:
        return "rising"
    if growth_180d > -0.1:
        return "stable"
    return "declining"


def _detect_conversion_signal(cr) -> str:
    if cr is None:
        return "unknown"
    if cr >= 0.03:
        return "high"
    if cr >= 0.015:
        return "medium"
    if cr >= 0.005:
        return "low"
    return "critical_low"


# ── Public API ────────────────────────────────────────────────────────────────

def parse_products_csv(content_bytes: bytes, niche_name: str = "") -> dict:
    """Parse Products Tab CSV → structured dict."""
    text = content_bytes.decode("utf-8", errors="replace").lstrip("\ufeff")
    lines = text.splitlines()

    # Extract niche name from pre-header lines if not provided
    if not niche_name:
        for line in lines[:10]:
            if "Niche:" in line:
                niche_name = line.split("Niche:")[-1].strip().strip('"')
                break

    header_idx = _find_header_idx(lines, "ASIN")
    df = pd.read_csv(
        io.StringIO("\n".join(lines[header_idx:])),
        dtype=str,
        on_bad_lines="skip",
    )
    df.columns = [c.strip() for c in df.columns]
    col = _col_map(df.columns)

    products = []
    for rank, (_, row) in enumerate(df.iterrows(), start=1):
        asin = _v(row, col, "asin")
        if not asin or len(str(asin)) < 4:
            continue

        launch_raw = _v(row, col, "launch_date")
        months = _months_since(launch_raw)
        total_ratings = _to_int(_v(row, col, "total_ratings"))
        velocity = round(total_ratings / months, 1) if (total_ratings and months) else None

        name = _v(row, col, "product_name") or ""
        ptype, pnote = _classify_product_type(name, niche_name)

        click_share = _pct_to_decimal(_v(row, col, "click_share"))

        velocity_flag = None
        if velocity and velocity >= 100:
            velocity_flag = f"⚠️ ВНИМАНИЕ: аномально высокая скорость отзывов (~{int(velocity)}/мес) — возможна манипуляция"
        elif velocity and velocity >= 50:
            velocity_flag = f"⚠️ Повышенная скорость отзывов (~{int(velocity)}/мес) — проверить"

        products.append({
            "rank_by_clicks": rank,
            "product_name": name,
            "asin": asin,
            "brand": _v(row, col, "brand"),
            "category": _v(row, col, "category"),
            "launch_date": launch_raw,
            "click_count_360d": _to_int(_v(row, col, "click_count")),
            "click_share_360d": click_share,
            "avg_price_360d": _to_float(_v(row, col, "avg_price")),
            "total_ratings": total_ratings,
            "avg_rating": _to_float(_v(row, col, "avg_rating")),
            "avg_bsr": _to_int(_v(row, col, "avg_bsr")),
            "avg_sellers_count": _to_int(_v(row, col, "avg_sellers")),
            "product_type": ptype,
            "product_type_note": pnote,
            "review_velocity_per_month": velocity,
            "velocity_flag": velocity_flag,
        })

    direct = [p for p in products if p["product_type"] == "direct"]
    adjacent = [p for p in products if p["product_type"] == "adjacent"]

    def safe_sum_cs(lst):
        return sum(p["click_share_360d"] or 0 for p in lst)

    top5_cs = safe_sum_cs(products[:5])
    top10_cs = safe_sum_cs(products[:10])
    direct_cs = safe_sum_cs(direct)
    adjacent_cs = safe_sum_cs(adjacent)

    prices = [p["avg_price_360d"] for p in products if p["avg_price_360d"]]
    ratings = [p["avg_rating"] for p in products if p["avg_rating"]]
    ratings_counts = [p["total_ratings"] for p in products if p["total_ratings"]]
    brands = set(p["brand"] for p in products if p["brand"])

    return {
        "source_type": "products_csv",
        "confidence": "primary",
        "niche_name": niche_name,
        "total_products": len(products),
        "products": products,
        "market_structure": {
            "top5_click_share": round(top5_cs, 4),
            "top10_click_share": round(top10_cs, 4),
            "unique_brands": len(brands),
            "avg_price_all": round(sum(prices) / len(prices), 2) if prices else None,
            "median_price": round(sorted(prices)[len(prices) // 2], 2) if prices else None,
            "price_range": {"min": min(prices), "max": max(prices)} if prices else {},
            "avg_rating_all": round(sum(ratings) / len(ratings), 2) if ratings else None,
            "avg_total_ratings": int(sum(ratings_counts) / len(ratings_counts)) if ratings_counts else None,
            "direct_product_count": len(direct),
            "direct_product_click_share": round(direct_cs, 4),
            "adjacent_product_click_share": round(adjacent_cs, 4),
            "true_addressable_market_pct": round(direct_cs, 4),
        },
    }


def parse_search_terms_csv(content_bytes: bytes) -> dict:
    """Parse Search Terms Tab CSV → structured dict."""
    text = content_bytes.decode("utf-8", errors="replace").lstrip("\ufeff")
    lines = text.splitlines()

    header_idx = _find_header_idx(lines, "Search Term")
    df = pd.read_csv(
        io.StringIO("\n".join(lines[header_idx:])),
        dtype=str,
        on_bad_lines="skip",
    )
    df.columns = [c.strip() for c in df.columns]
    col = _col_map(df.columns)

    terms = []
    for rank, (_, row) in enumerate(df.iterrows(), start=1):
        term = _v(row, col, "search_term")
        if not term or str(term) in ("nan", ""):
            continue

        growth_90d = _pct_to_decimal(_v(row, col, "growth_90d"))
        growth_180d = _pct_to_decimal(_v(row, col, "growth_180d"))
        click_share = _pct_to_decimal(_v(row, col, "click_share"))
        conversion_rate = _pct_to_decimal(_v(row, col, "conversion_rate"))

        # Top 3 clicked products
        top_products = []
        for n in range(1, 4):
            t_key = f"top_product_{n}_title"
            a_key = f"top_product_{n}_asin"
            title = _v(row, col, t_key) or ""
            asin = _v(row, col, a_key) or ""
            if title or asin:
                top_products.append({"rank": n, "title": title, "asin": asin})

        terms.append({
            "rank_by_volume": rank,
            "term": str(term).strip(),
            "volume_360d": _to_int(_v(row, col, "volume")),
            "growth_90d": growth_90d,
            "growth_180d": growth_180d,
            "click_share_360d": click_share,
            "conversion_rate_360d": conversion_rate,
            "top_products": top_products,
            "language": "es" if _is_spanish(str(term)) else "en",
            "intent_cluster": _detect_cluster(str(term)),
            "momentum": _detect_momentum(growth_180d),
            "conversion_signal": _detect_conversion_signal(conversion_rate),
        })

    total_volume = sum(t["volume_360d"] or 0 for t in terms)
    return {
        "source_type": "search_terms_csv",
        "confidence": "primary",
        "total_terms": len(terms),
        "total_volume_360d": total_volume,
        "terms": terms,
    }

"""
Cross-reference engine — compares the same field across multiple data sources.
Produces confirmed facts, signals, and conflicts.
"""


def _close(a, b, tolerance=0.05) -> bool:
    """Check if two numeric values are within tolerance of each other."""
    if a is None or b is None:
        return False
    try:
        fa, fb = float(a), float(b)
        if fa == 0 and fb == 0:
            return True
        ref = max(abs(fa), abs(fb))
        return abs(fa - fb) / ref <= tolerance
    except (TypeError, ValueError):
        return str(a).strip().lower() == str(b).strip().lower()


# Field definitions: (display_name, paths_per_source)
# Each path is (source_key, dict_path) where dict_path is dot-notation
_FIELDS = [
    ("Search Volume 360d", [
        ("products_csv",       None),                          # not in products CSV
        ("search_terms_csv",   "total_volume_360d"),
        ("competition_table",  "product_and_search.search_volume.360d"),
        ("niche_overview",     "overview.search_volume_360d"),
        ("ai_text",            "overview.search_volume_360d"),
        ("chrome_ext",         "overview.search_volume_360d"),
    ]),
    ("Avg Selling Price", [
        ("products_csv",       "market_structure.avg_price_all"),
        ("competition_table",  "product_and_search.avg_selling_price.360d"),
        ("niche_overview",     "overview.avg_price_360d"),
        ("ai_text",            None),
        ("chrome_ext",         "overview.avg_price_360d"),
    ]),
    ("Brand Count", [
        ("products_csv",       "market_structure.unique_brands"),
        ("competition_table",  "brands_and_selling_partners.brand_count.today"),
        ("ai_text",            "overview.brand_count"),
        ("chrome_ext",         None),
    ]),
    ("Top 5 Click Share", [
        ("products_csv",       "market_structure.top5_click_share"),
        ("competition_table",  "product_and_search.top5_products_click_share.today"),
        ("ai_text",            None),
        ("chrome_ext",         None),
    ]),
    ("Search Conversion Rate", [
        ("search_terms_csv",   None),                          # aggregate avg
        ("competition_table",  "product_and_search.search_conversion_rate.today"),
        ("ai_text",            "overview.conversion_rate"),
        ("chrome_ext",         None),
    ]),
    ("Avg Review Count", [
        ("products_csv",       "market_structure.avg_total_ratings"),
        ("competition_table",  "customer_experience.avg_review_count.today"),
        ("ai_text",            None),
    ]),
    ("Avg Rating", [
        ("products_csv",       "market_structure.avg_rating_all"),
        ("competition_table",  "customer_experience.avg_rating.today"),
        ("ai_text",            None),
    ]),
]


def _get_nested(d: dict, path: str):
    """Access a nested dict value by dot-notation path."""
    if not path or not isinstance(d, dict):
        return None
    parts = path.split(".")
    current = d
    for p in parts:
        if not isinstance(current, dict):
            return None
        current = current.get(p)
    return current


def cross_reference(schema: dict) -> dict:
    """
    schema: unified schema dict with keys matching source_key values above
    Returns: {confirmed_facts, signals, conflicts}
    """
    confirmed_facts = []
    signals = []
    conflicts = []

    for field_name, source_paths in _FIELDS:
        values = {}
        for source_key, path in source_paths:
            if path is None:
                continue
            source_data = schema.get(source_key)
            if not source_data:
                continue
            val = _get_nested(source_data, path)
            if val is not None:
                values[source_key] = val

        if len(values) == 0:
            continue

        source_keys = list(values.keys())
        if len(values) == 1:
            signals.append({
                "field": field_name,
                "source": source_keys[0],
                "value": values[source_keys[0]],
                "note": "Только один источник — требует подтверждения",
            })
            continue

        # Compare all pairs
        all_agree = True
        disagreeing_pairs = []
        compared = list(values.items())
        for i in range(len(compared)):
            for j in range(i + 1, len(compared)):
                sk1, v1 = compared[i]
                sk2, v2 = compared[j]
                if not _close(v1, v2):
                    all_agree = False
                    disagreeing_pairs.append((sk1, v1, sk2, v2))

        # Priority order for conflict resolution
        priority = ["products_csv", "search_terms_csv", "niche_overview",
                    "competition_table", "chrome_ext", "ai_text"]
        best_source = None
        best_val = None
        for p in priority:
            if p in values:
                best_source = p
                best_val = values[p]
                break

        if all_agree:
            confirmed_facts.append({
                "fact": f"{field_name}: {best_val}",
                "sources": source_keys,
                "values": values,
            })
        else:
            conflicts.append({
                "field": field_name,
                "values": values,
                "resolution": f"Принято: {best_val} (источник: {best_source})",
                "disagreements": [
                    f"{p[0]}={p[1]} vs {p[2]}={p[3]}" for p in disagreeing_pairs
                ],
            })

    return {
        "confirmed_facts": confirmed_facts,
        "signals": signals,
        "conflicts": conflicts,
    }

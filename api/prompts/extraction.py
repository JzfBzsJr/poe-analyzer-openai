"""
Extraction prompts for each POE data source type.
Each prompt instructs Claude to extract data and return ONLY valid JSON.
"""

PROMPT_IDENTIFY_IMAGE = """
You are analyzing an Amazon Product Opportunity Explorer (POE) screenshot.
Identify which screen type this is and return ONLY one of these exact strings:
- niche_overview
- competition_table
- demand_chart
- topic_impact_positive
- topic_impact_negative
- returns_insights
- unknown

Return ONLY the string, nothing else.
"""

PROMPT_NICHE_OVERVIEW = """
You are extracting data from an Amazon POE "Niche Details" overview screenshot.
Extract all visible metric values and return ONLY valid JSON:

{
  "screen_type": "niche_overview",
  "niche_name": "<text shown as niche title>",
  "market": "<country if visible, else null>",
  "last_updated": "<date string>",
  "overview": {
    "search_volume_360d": <integer>,
    "search_volume_growth_180d": <decimal, e.g. 31.19% → 0.3119>,
    "num_top_clicked_products": <integer>,
    "avg_price_360d": <decimal, digits only, no $>,
    "units_sold_range": "<string e.g. '500-750'>",
    "return_rate_360d": <decimal, e.g. 1.30% → 0.013>
  }
}

Rules: percentages → decimal | $ → number only | null if not visible.
Return ONLY valid JSON, no explanation.
"""

PROMPT_COMPETITION_TABLE = """
You are extracting data from an Amazon POE Competition Overview table screenshot.
The table has columns: Today | 90 days ago | 360 days ago.
Extract ALL rows from ALL three sections and return ONLY valid JSON:

{
  "screen_type": "competition_overview",
  "product_and_search": {
    "product_count":                {"today": <int>, "90d": <int>, "360d": <int>},
    "sponsored_product_count":      {"today": <int>, "90d": <int>, "360d": <int>},
    "prime_product_count":          {"today": <int>, "90d": <int>, "360d": <int>},
    "top5_products_click_share":    {"today": <decimal>, "90d": <decimal>, "360d": <decimal>},
    "top20_products_click_share":   {"today": <decimal>, "90d": <decimal>, "360d": <decimal>},
    "avg_selling_price":            {"today": <decimal>, "90d": <decimal>, "360d": <decimal>},
    "search_volume":                {"today": <int>, "90d": <int>, "360d": <int>},
    "search_conversion_rate":       {"today": <decimal>, "90d": <decimal>, "360d": <decimal>},
    "new_product_count":            {"today": <int>, "90d": <int>, "360d": <int>},
    "success_launch_product_count": {"today": <int>, "90d": <int>, "360d": <int>}
  },
  "brands_and_selling_partners": {
    "brand_count":                   {"today": <int>, "90d": <int>, "360d": <int>},
    "top5_brands_click_share":       {"today": <decimal>, "90d": <decimal>, "360d": <decimal>},
    "top20_brands_click_share":      {"today": <decimal>, "90d": <decimal>, "360d": <decimal>},
    "avg_age_brands_days":           {"today": <int>, "90d": <int>, "360d": <int>},
    "selling_partner_count":         {"today": <int>, "90d": <int>, "360d": <int>},
    "avg_age_selling_partners_days": {"today": <int>, "90d": <int>, "360d": <int>}
  },
  "customer_experience": {
    "avg_rating":            {"today": <decimal>, "90d": <decimal>, "360d": <decimal>},
    "avg_out_of_stock_rate": {"today": <decimal>, "90d": <decimal>, "360d": <decimal or null>},
    "avg_bsr":               {"today": <int>, "90d": <int>, "360d": <int>},
    "avg_review_count":      {"today": <int>, "90d": <int>, "360d": <int>}
  }
}

Rules: % → decimal | $ → number only | "--" or missing → null | remove "days" suffix.
Return ONLY valid JSON, no explanation.
"""

PROMPT_DEMAND_CHART = """
You are extracting data from an Amazon POE "Demand Overview" chart screenshot.
This chart shows two data series over approximately 2 years:
- Primary series (orange/bar): Search Volume (left axis)
- Secondary series (blue/line): Search Conversion Rate (right axis)

Extract all visible data and return ONLY valid JSON:

{
  "screen_type": "demand_trend_chart",
  "primary_series": "Search Volume",
  "secondary_series": "Search Conversion Rate",
  "axes": {
    "x_start": "<YYYY-MM-DD>",
    "x_end": "<YYYY-MM-DD>",
    "primary_y_min": <int>,
    "primary_y_max": <int>,
    "secondary_y_min": <decimal>,
    "secondary_y_max": <decimal>
  },
  "trend_summary": {
    "primary_trend": "<growing|declining|seasonal|stable>",
    "secondary_trend": "<growing|declining|seasonal|stable>",
    "overall_description": "<2-3 sentences describing the visible pattern>"
  },
  "notable_points": [
    {"date_approx": "<YYYY-MM>", "primary_value": <int or null>, "secondary_value": <decimal or null>, "label": "<peak|trough|inflection>"}
  ],
  "seasonality": {
    "detected": <bool>,
    "peak_months": ["<month name>"],
    "low_months": ["<month name>"],
    "pattern_notes": "<text>"
  },
  "conversion_rate_interpretation": {
    "current_level": "<low|medium|high>",
    "signal": "<market_unsatisfied|market_neutral|market_satisfied>",
    "notes": "<brief interpretation>"
  }
}

Conversion rate thresholds: ≤1% = market_unsatisfied | 1-6% = market_neutral | ≥6% = market_satisfied.
Return ONLY valid JSON, no explanation.
"""

PROMPT_TOPIC_IMPACT = """
You are extracting data from an Amazon POE Topic Impact screenshot.
This screenshot contains TWO panels:
- LEFT panel: horizontal bar chart showing topic impact on star rating (-1 to +1 scale)
  Orange bars = Top 25% Products | Dark blue bars = All Products
- RIGHT panel: line chart showing trend of one topic's mention rate over 6 months
  Orange line = Top 25% Products | Dark blue line = All Products

The tab shown is: {tab}  (positive_topics or negative_topics)

Extract all visible data and return ONLY valid JSON:

{
  "screen_type": "topic_impact_and_trend",
  "tab": "<positive_topics|negative_topics>",
  "impact_chart": {
    "topics": [
      {
        "topic": "<topic name>",
        "top25_impact": <decimal, e.g. +0.15 or -0.09>,
        "all_products_impact": <decimal>,
        "gap": <decimal, top25 minus all_products>,
        "gap_direction": "<top25_better|all_better|equal>",
        "classification": "<differentiator|table_stakes|equal_importance>"
      }
    ]
  },
  "trend_chart": {
    "topic_shown": "<topic name from dropdown>",
    "data_points": [
      {"month": "<YYYY-MM>", "top25_pct": <decimal>, "all_products_pct": <decimal>}
    ],
    "top25_trend": "<rising|declining|stable|volatile>",
    "all_products_trend": "<rising|declining|stable|volatile>"
  }
}

Return ONLY valid JSON, no explanation.
"""

PROMPT_RETURNS = """
You are extracting data from an Amazon POE Returns Insights screenshot.
This screenshot contains TWO panels:
- LEFT panel: table of return topics with % Mentions column
- RIGHT panel: line chart showing trend of one return topic over time (single series)

% Mentions = percentage of returned products citing this reason.

Extract all visible data and return ONLY valid JSON:

{
  "screen_type": "returns_insights_and_trend",
  "return_topics": [
    {
      "topic": "<topic name>",
      "return_mention_rate": <decimal, e.g. 12.92% → 0.1292>,
      "severity": "<critical|major|minor>"
    }
  ],
  "return_trend": {
    "topic_shown": "<topic name>",
    "data_points": [{"month": "<YYYY-MM>", "return_pct": <decimal>}],
    "trend_direction": "<rising|declining|stable|volatile>"
  }
}

Severity: ≥15% → critical | 5-15% → major | <5% → minor.
Return ONLY valid JSON, no explanation.
"""

PROMPT_AI_TEXT_REPORT = """
You are extracting structured data from an Amazon POE "Top Niche Insights" AI-generated text report.
This is a SECONDARY source — extract only what is explicitly stated, do not infer.

Extract all data and return ONLY valid JSON:

{
  "source_type": "ai_text_report",
  "confidence": "secondary",
  "niche_name": "<niche name>",
  "overview": {
    "revenue_range_360d": {"min": <number or null>, "max": <number or null>},
    "search_volume_360d": <int or null>,
    "search_volume_growth_yoy": <decimal or null>,
    "conversion_rate": <decimal or null>,
    "brand_count": <int or null>,
    "brand_count_growth_yoy": <decimal or null>,
    "successful_launches_past_year": <int or null>
  },
  "seasonality": {
    "peaks": [{"period": "<month/quarter>", "search_volume_approx": <int or null>}],
    "lows": [{"period": "<month/quarter>", "search_volume_approx": <int or null>}],
    "notes": "<key seasonal pattern>"
  },
  "product_features": {
    "top_features": ["<feature1>", "<feature2>"],
    "top_combinations": ["<combo1>"],
    "format_distribution": ["<format>"],
    "emerging_trends": ["<trend>"]
  },
  "demographics": {
    "primary_gender": "<male|female|mixed>",
    "primary_age_range": "<e.g. 25-55>",
    "income_level": "<low|middle|upper-middle|high>",
    "key_motivations": ["<motivation>"],
    "segments": [{"name": "<segment>", "description": "<>"}]
  },
  "search_terms": {
    "fast_growing": [{"term": "<>", "growth_yoy": <decimal or null>}],
    "high_converting": [{"term": "<>", "conversion_rate": <decimal or null>}],
    "top_categories": [{"category": "<>", "volume_approx": <int or null>}]
  },
  "pricing": {
    "segments": [{"range": "<$X-$Y>", "niche_share": <decimal or null>, "notes": "<>"}],
    "sweet_spot": {"min": <decimal or null>, "max": <decimal or null>, "rationale": "<>"}
  }
}

Rules: % → decimal | "+" suffixes = lower bound | vague values → null.
Return ONLY valid JSON, no explanation.
"""

PROMPT_CHROME_EXT_NARRATIVE = """
You are extracting structured data from the narrative/analysis sections of an Amazon POE Chrome Extension export.
Focus ONLY on the text sections (Niche Dynamics, Customer Reviews analysis, Demographics, Search Terms analysis, Pricing analysis).
Do NOT re-process table data — only narrative insights.

Extract and return ONLY valid JSON matching this schema:

{
  "source_type": "ai_text_report",
  "confidence": "secondary",
  "niche_name": "<niche name>",
  "overview": {
    "revenue_range_360d": {"min": <number or null>, "max": <number or null>},
    "search_volume_growth_yoy": <decimal or null>,
    "brand_count_growth_yoy": <decimal or null>,
    "successful_launches_past_year": <int or null>
  },
  "seasonality": {
    "peaks": [{"period": "<>", "search_volume_approx": <int or null>}],
    "lows": [{"period": "<>", "search_volume_approx": <int or null>}],
    "notes": "<key seasonal pattern>"
  },
  "product_features": {
    "top_features": ["<feature>"],
    "top_combinations": ["<combo>"],
    "emerging_trends": ["<trend>"]
  },
  "demographics": {
    "primary_gender": "<male|female|mixed>",
    "primary_age_range": "<>",
    "income_level": "<>",
    "key_motivations": ["<motivation>"],
    "segments": [{"name": "<>", "description": "<>"}]
  },
  "pricing": {
    "segments": [{"range": "<$X-$Y>", "niche_share": <decimal or null>, "notes": "<>"}],
    "sweet_spot": {"min": <decimal or null>, "max": <decimal or null>, "rationale": "<>"}
  }
}

Return ONLY valid JSON, no explanation.
"""

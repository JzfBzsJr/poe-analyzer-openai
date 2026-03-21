---
name: poe-analysis-brain
description: Анализ данных Amazon Product Opportunity Explorer (POE) — извлечение, кросс-референс и синтез из CSV, скриншотов и AI-текстов
---

# POE Niche Analysis Brain

## Назначение
Анализ данных Amazon Product Opportunity Explorer (POE) из нескольких источников.
Принимает любую комбинацию файлов и скриншотов, извлекает данные, сопоставляет источники и формирует структурированный анализ ниши.

---

## Принципы работы

### Иерархия достоверности источников
| Приоритет | Источник | Тип | Уровень доверия |
|---|---|---|---|
| 1 | CSV/XLSX файлы (Products Tab, Search Terms Tab) | Первичный | Максимальный |
| 2 | Скриншоты POE (Competition Table, Topic Impact, Charts) | Первичный | Высокий |
| 3 | Top Niche Insights (AI-generated текст) | Вторичный | Индикативный |

### Правило кросс-референса
- Одно значение в 2+ источниках → **подтверждённый факт** ✅
- Значение только в одном источнике → **сигнал для проверки** ⚠️
- Расхождение между источниками → **флаг конфликта** ⚡

### Правило выводов
- **Промежуточные этапы**: формулировать как `⚠️ Обратить внимание: [наблюдение]. Требует подтверждения.`
- **Твёрдые выводы**: только при подтверждении 2+ источниками. Формат: `✅ Подтверждено: [вывод] — источники: [X, Y]`
- **Исключение**: очевидные факты (рейтинг 2.6★, дата запуска в будущем) → твёрдый вывод с указанием основания

---

### Правило языка и формулировок

**Язык вывода**: русский. Не смешивать с английским без необходимости.

**ЗАПРЕЩЕНО использовать:**
- Академический жаргон и редкие термины, непонятные без словаря: "бифурцирован", "дихотомия", "конвергенция", "эмерджентный" и т.п. — заменять простыми словами ("рынок разделён на два сегмента", "рынок делится на два типа покупателей")
- Военные и художественные метафоры: "непреодолимый бастион", "лобовая атака", "укреплённые позиции", "захват рынка" — заменять деловыми формулировками ("конкуренты с сильными позициями", "высокий барьер входа")
- Английские термины там, где есть русский эквивалент: "emerging под-ниши" → "формирующиеся сегменты", "top performers" → "лидеры ниши", "pain points" → "проблемы покупателей", "insights" → "наблюдения"

**ОБЯЗАТЕЛЬНО:**
- Писать так, чтобы человек без специального образования понял с первого прочтения
- Если нет простого русского эквивалента — кратко объяснить термин в скобках
- Использовать конкретные цифры вместо оценочных прилагательных: не "высокая конкуренция", а "80 товаров в нише, топ-5 занимают 23% кликов"

---

## Порядок обработки
1. CSV файлы (Products Tab, Search Terms Tab) — сначала
2. Скриншоты Competition Table, Niche Overview
3. Topic Impact + Trends скриншоты
4. Returns Insights скриншот
5. AI Text Report (Top Niche Insights) — последним
6. Кросс-референс всех источников
7. Финальный синтез

---

## ОБЯЗАТЕЛЬНЫЙ ШАГ 0 — Инвентаризация файлов

**ПЕРЕД ЛЮБЫМ АНАЛИЗОМ** выполни следующее:

1. Составь список ВСЕХ полученных файлов и изображений
2. Для каждого файла — **открой и прочитай** его содержимое (не пропускай ни один)
3. Для каждого изображения — **просмотри** его содержимое
4. Определи тип каждого файла по правилам из Блока 1
5. Выведи чеклист в формате:

```
📋 Получено файлов: N
[✓] filename1.csv → тип: products_csv
[✓] filename2.csv → тип: search_terms_csv
[✓] screenshot1.png → тип: competition_overview (просмотрен)
[✓] report.txt → тип: ai_text_report (прочитан)
```

**СТОП**: если хотя бы один файл не открыт — НЕ начинай анализ. Открой его первым.

> Ошибка "файл получен но не обработан" недопустима. Текстовые файлы (.txt, .docx) часто содержат AI Text Report — он должен обрабатываться последним, но открыт и прочитан должен быть в Шаге 0.

---

## БЛОК 1 — Идентификация типа данных

Перед обработкой определи тип каждого входящего файла/скриншота:

```
ПРАВИЛО ИДЕНТИФИКАЦИИ:
- Файл .csv с колонкой "Search Term" → Search Terms Tab CSV
- Файл .csv с колонкой "ASIN" + "Niche Click Count" → Products Tab CSV
- Скриншот с "Niche Details" + карточки метрик → Niche Overview Screen
- Скриншот с таблицей Today/90d/360d → Competition Overview Table
- Скриншот с "Demand Overview" + два графика → Demand Trend Chart
- Скриншот с горизонтальными барами + линейный график справа → Topic Impact + Trend
- Скриншот с таблицей Topic/%Mentions + линейный график → Returns Insights
- Текстовый файл .txt/.docx с разделами "Niche Dynamics", "Feature Analysis" → AI Text Report
```

---

## БЛОК 2 — Извлечение данных по типам

### 2.1 Niche Overview Screen (скриншот)
```
Экран: "Niche Details" overview page.
Извлечь все значения и вернуть JSON:

{
  "screen_type": "niche_overview",
  "niche_name": "<текст под изображением продукта>",
  "market": "<страна>",
  "last_updated": "<дата>",
  "overview": {
    "search_volume_360d": <int>,
    "search_volume_growth_180d": <decimal, 31.19% → 0.3119>,
    "num_top_clicked_products": <int>,
    "avg_price_360d": <decimal, без $>,
    "units_sold_range": "<строка, напр. '500-750'>",
    "return_rate_360d": <decimal, 1.30% → 0.013>
  }
}
Правила: % → decimal | $ → только число | null если не видно
```

### 2.2 Competition Overview Table (скриншот)
```
Таблица: Today | 90 days ago | 360 days ago. Три секции.
Извлечь ВСЕ строки:

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
    "brand_count":                  {"today": <int>, "90d": <int>, "360d": <int>},
    "top5_brands_click_share":      {"today": <decimal>, "90d": <decimal>, "360d": <decimal>},
    "top20_brands_click_share":     {"today": <decimal>, "90d": <decimal>, "360d": <decimal>},
    "avg_age_brands_days":          {"today": <int>, "90d": <int>, "360d": <int>},
    "selling_partner_count":        {"today": <int>, "90d": <int>, "360d": <int>},
    "avg_age_selling_partners_days":{"today": <int>, "90d": <int>, "360d": <int>}
  },
  "customer_experience": {
    "avg_rating":            {"today": <decimal>, "90d": <decimal>, "360d": <decimal>},
    "avg_out_of_stock_rate": {"today": <decimal>, "90d": <decimal>, "360d": <decimal or null>},
    "avg_bsr":               {"today": <int>, "90d": <int>, "360d": <int>},
    "avg_review_count":      {"today": <int>, "90d": <int>, "360d": <int>}
  }
}
Правила: % → decimal | $ → число | "--" → null | "days" → убрать суффикс
```

**Аналитические правила для Competition Table:**
- Top 5 click share 360d→today ПАДАЕТ → рынок открывается, сигнал входа
- Top 5 click share РАСТЁТ → рынок концентрируется
- Out-of-stock ≥30% → ⚠️ критический дефицит товаров
- Out-of-stock 15–30% → ⚠️ нехватка предложения
- avg_review_count <500 → низкий барьер входа
- avg_review_count 500–1000 → средний барьер
- avg_review_count >1000 → ⚠️ высокий барьер (преодолим с сильным УТП)
- avg_rating <4.2 → покупатели не удовлетворены — возможность войти с лучшим продуктом
- avg_rating 4.2–4.4 → нейтрально, нужна дифференциация не по качеству
- avg_rating >4.4 → сильные игроки, конкурировать нужно по фичам/цене/позиционированию
- sponsored/product_count >80% → ⚠️ PPC обязателен с первого дня
- sponsored/product_count 50–80% → PPC рекомендован
- sponsored/product_count <50% → органический запуск возможен
- avg_selling_price растёт 360d→today → премиумизация рынка
- success_launch >new_product_count → рынок принимает новых игроков

### 2.3 Demand Trend Chart (скриншот)
```
Экран: "Demand Overview" — два ряда за ~2 года.
Primary Series (оранжевый) = Search Volume (левая ось)
Secondary Series (синий) = Search Conversion Rate (правая ось)

{
  "screen_type": "demand_trend_chart",
  "primary_series": "<название>",
  "secondary_series": "<название>",
  "axes": {
    "x_start": "<YYYY-MM-DD>", "x_end": "<YYYY-MM-DD>",
    "primary_y_min": <int>, "primary_y_max": <int>,
    "secondary_y_min": <decimal>, "secondary_y_max": <decimal>
  },
  "trend_summary": {
    "primary_trend": "<growing/declining/seasonal/stable>",
    "secondary_trend": "<growing/declining/seasonal/stable>",
    "overall_description": "<2-3 предложения>"
  },
  "notable_points": [
    {"date_approx": "<YYYY-MM>", "primary_value": <int or null>,
     "secondary_value": <decimal or null>, "label": "<peak/trough/inflection>"}
  ],
  "seasonality": {
    "detected": <bool>, "peak_months": [], "low_months": [], "pattern_notes": "<текст>"
  },
  "conversion_rate_interpretation": {
    "current_level": "<low/medium/high>",
    "signal": "<market_unsatisfied/market_neutral/market_satisfied>",
    "periods_of_low_conversion": [],
    "periods_of_high_conversion": []
  }
}
```

**Правила интерпретации Search Conversion Rate:**
- ≤1.0% → `market_unsatisfied`: высокий поисковый спрос, но покупатели не конвертируются — существующие продукты не удовлетворяют запросу, есть продуктовый гэп
- 1.0–5.0% → `market_neutral`: нормальный рынок, покупатели избирательны
- ≥6.0–8.0%+ → `market_satisfied`: продукты хорошо соответствуют запросу, сложнее вытеснить лидеров
- Высокий объём + низкая конверсия → ⚠️ большой неудовлетворённый спрос
- Низкий объём + высокая конверсия → ⚠️ лояльная но небольшая аудитория

### 2.4 Products Tab CSV
```
Файл: "Niche Details - Products Tab"
Колонки: Product Name | ASIN | Brand | Category | Launch Date |
Niche Click Count (360d) | Click Share (360d) | Avg Selling Price (360d) |
Total Ratings | Avg Customer Rating | Avg BSR | Avg # Sellers (360d)

ОБЯЗАТЕЛЬНО извлечь для КАЖДОГО продукта: avg_bsr и avg_sellers_count.
Эти поля нельзя пропускать — BSR используется для оценки реальных продаж,
Avg Sellers — для оценки конкуренции на уровне листинга.

{
  "source_type": "products_csv",
  "confidence": "primary",
  "niche_name": "<из заголовка>",
  "last_updated": "<из заголовка>",
  "total_products": <int>,
  "products": [
    {
      "rank_by_clicks": <int>,
      "product_name": "<полное название>",
      "asin": "<ASIN>",
      "brand": "<бренд>",
      "category": "<категория>",
      "launch_date": "<YYYY-MM-DD>",
      "click_count_360d": <int>,
      "click_share_360d": <decimal>,
      "avg_price_360d": <decimal>,
      "total_ratings": <int>,
      "avg_rating": <decimal>,
      "avg_bsr": <int>,
      "avg_sellers_count": <int>,
      "product_type": "<direct/adjacent/unrelated>",
      "product_type_note": "<если не direct — объяснить>",
      "review_velocity_per_month": <decimal>
    }
  ],
  "market_structure": {
    "top5_click_share": <decimal>,
    "top10_click_share": <decimal>,
    "unique_brands": <int>,
    "avg_price_all": <decimal>,
    "median_price": <decimal>,
    "price_range": {"min": <decimal>, "max": <decimal>},
    "avg_rating_all": <decimal>,
    "avg_total_ratings": <int>,
    "direct_product_click_share": <decimal>,
    "adjacent_product_click_share": <decimal>,
    "true_addressable_market_pct": <decimal>
  }
}
```

**Аналитические правила для Products CSV:**

*Типы продуктов (ОБЯЗАТЕЛЬНО разделять):*
- "direct" — точное соответствие поисковому запросу (электрический массажёр, LED-устройство)
- "adjacent" — смежный другой тип (jade roller, gua sha, ice roller, eye massager)
- "unrelated" — другая категория (крем, праймер, масло)
→ Для каждого adjacent/unrelated: `"ДРУГОЙ ТИП ТОВАРА: [название] (ASIN: X) — [jade roller/eye massager/etc.] появляется в результатах по запросу '[ниша]', но НЕ является прямым конкурентом"`
→ Рассчитать true_addressable_market только по "direct" продуктам

*Аномалии отзывов:*
- review_velocity = total_ratings / месяцев с launch_date
- velocity ≥100/мес → ⚠️ `"ВНИМАНИЕ: [ASIN] набирает ~X отзывов/мес — аномально высокая скорость. Возможна манипуляция отзывами. Использовать с осторожностью."`
- velocity 50–99/мес → ⚠️ повышенная скорость, проверить
- avg_rating >4.8 AND total_ratings <100 → ⚠️ подозрительно высокий рейтинг при малом числе отзывов
- avg_rating <3.5 AND click_count >1000 → ⚠️ плохой товар с большим трафиком — вероятно PPC
- launch_date в будущем → ⚠️ аномалия данных

*Ценовой sweet spot:*
Найти диапазон с максимальным click_share / количество_продуктов

### 2.5 Search Terms Tab CSV
```
Файл: "Niche Details - Search Terms Tab"
Колонки: Search Term | Search Volume (360d) | Growth (90d) | Growth (180d) |
Click Share (360d) | Search Conversion Rate (360d) |
Top Clicked Product 1 Title | Top Clicked Product 1 ASIN |
Top Clicked Product 2 Title | Top Clicked Product 2 ASIN |
Top Clicked Product 3 Title | Top Clicked Product 3 ASIN

ОБЯЗАТЕЛЬНО извлечь для КАЖДОГО термина все три продукта (title + ASIN).
Эти колонки показывают, какие конкретные продукты забирают клики по каждому
запросу — критично для анализа конкуренции на уровне ключевых слов.
Если продукт 2 или 3 отсутствует в строке — записать null.

{
  "source_type": "search_terms_csv",
  "confidence": "primary",
  "total_terms": <int>,
  "total_volume_360d": <int>,
  "terms": [
    {
      "rank_by_volume": <int>,
      "term": "<запрос>",
      "volume_360d": <int>,
      "growth_90d": <decimal>,
      "growth_180d": <decimal>,
      "click_share_360d": <decimal>,
      "conversion_rate_360d": <decimal>,
      "top_products": [
        {"title": "<>", "asin": "<>", "rank": 1},
        {"title": "<>", "asin": "<>", "rank": 2},
        {"title": "<>", "asin": "<>", "rank": 3}
      ],
      "language": "<en/es/other>",
      "intent_cluster": "<см. кластеры ниже>",
      "momentum": "<rising/declining/stable/exploding>",
      "conversion_signal": "<high/medium/low/critical_low>"
    }
  ],
  "clusters": [
    {"name": "<кластер>", "total_volume": <int>, "volume_share": <decimal>,
     "avg_conversion": <decimal>, "avg_growth_180d": <decimal>, "momentum": "<>"}
  ],
  "opportunity_signals": {
    "high_conversion_growing": [],
    "exploding_growth": [],
    "declining": [],
    "underserved_intent": []
  }
}
```

**Кластеры поисковых запросов:**
- `general_massager` — "face massager", "facial massager", "face and neck massager"
- `lymphatic_drainage` — содержит: lymphatic, drainage, contour face
- `depuffing_sculpting` — depuffer, depuff, puffiness, sculptor, sculpt, slimming
- `red_light_led` — red light, LED, 7 color, light therapy
- `gua_sha_tools` — gua sha, jade roller, ice roller, roller
- `lifting_firming` — lift, lifting, firming, tightening, anti-aging, EMS
- `spanish_language` — masajeador, para la cara, de cara
- `device_generic` — "beauty device", "facial device", "face device"

**Momentum по growth_180d:**
- >100% → "exploding": ⚠️ тренд на начальной стадии, ранний вход имеет преимущество
- 20–100% → "rising"
- -10% до 20% → "stable"
- <-10% → "declining": ⚠️ нисходящий тренд

**Conversion Rate:**
- ≥3.0% → "high": высокий покупательский намерение
- 1.5–3.0% → "medium"
- 0.5–1.5% → "low"
- <0.5% → "critical_low": ⚠️ преимущественно информационные запросы

**Незакрытый интент (underserved):**
Если топ-3 продукта по запросу = adjacent/unrelated типы → ни один прямой продукт не занимает топ → незакрытая потребность

### 2.6 Customer Review Insights (текст или скриншот)
```
Данные охватывают ВСЕ продукты ниши — включая разные типы товаров.
Структура: Родительский топик (% от всех отзывов) → Подтопики (% внутри родительского)

{
  "source_type": "review_insights",
  "data_period": "last 6 months",
  "covers_all_product_types": true,
  "positive_topics": [
    {
      "topic": "<название>",
      "mention_rate": <decimal, от ВСЕХ отзывов>,
      "subtopics": [{"name": "<>", "share_within_topic": <decimal>, "sample_quotes": []}],
      "product_type_signal": "<all/massager_specific/brush_specific/skincare_specific/mixed>"
    }
  ],
  "negative_topics": [
    {
      "topic": "<название>",
      "mention_rate": <decimal>,
      "subtopics": [],
      "severity": "<critical/major/minor>",
      "product_type_signal": "<>"
    }
  ]
}
```

**Правила для Review Insights:**
- mention_rate от ВСЕХ отзывов ≥8% (негатив) → severity="critical"
- mention_rate 4–8% → severity="major"
- Обнаружение загрязнения данными: "bristles/brush" → щётки; "moisturizer/cream/hydrates" → скинкеа; "eye/migraine" → eye massager → флагировать как другой тип товара
- Топики в позитиве И негативе одновременно → высокая поляризация мнений

### 2.7 Topic Impact on Star Rating + Topic Mentions Trend (скриншот пары)
```
Два скриншота: Positive Topics и Negative Topics (каждый содержит два панели).

Левая панель: бар-чарт влияния на рейтинг (-1 до +1)
Правая панель: линейный тренд одного топика за 6 месяцев

Orange = Top 25% Products | Dark Blue = All Products

{
  "screen_type": "topic_impact_and_trend",
  "tab": "<positive_topics/negative_topics>",
  "impact_chart": {
    "topics": [
      {
        "topic": "<>",
        "top25_impact": <decimal>,
        "all_products_impact": <decimal>,
        "gap": <decimal>,
        "gap_direction": "<top25_better/all_better/equal>",
        "classification": "<differentiator/table_stakes/equal_importance>",
        "severity": "<critical/major/minor> (только для негативных>"
      }
    ]
  },
  "trend_chart": {
    "topic_shown": "<топик из дропдауна>",
    "data_points": [{"month": "<YYYY-MM>", "top25_pct": <decimal>, "all_products_pct": <decimal>}],
    "top25_trend": "<rising/declining/stable/volatile>",
    "all_products_trend": "<>",
    "anomalies": []
  }
}
```

**Аналитические правила Topic Impact:**

*Позитивные топики:*
- top25 gap >0.15 над all_products → "differentiator": атрибут лидеров
- all_products gap >0.2 над top25 → "table_stakes": базовое ожидание, за это не дают высокий балл у топ-продуктов
- "results_based" (Wrinkle, Efficiency, Glow, Skin Suitability) доминируют у top25 → покупатели лидеров платят за реальный эффект

*Негативные топики:*
- |impact| ≥0.07 → critical: основной убийца рейтинга
- |impact| 0.03–0.07 → major
- top25 значительно лучше all_products (gap >0.02) → лидеры решили эту проблему
- top25 значительно хуже (gap <-0.02) → ⚠️ более сложные/дорогие устройства имеют больше точек отказа

*Тренд:*
- Месяц к месяцу изменение >30% → аномалия: ротация когорты, сезон, или реальное изменение
- Негативный топик растёт в последние 2 месяца → ⚠️ нарастающая проблема

### 2.8 Returns Insights + Topic Returns Trend (скриншот)
```
Левая панель: таблица причин возвратов (Topic | % Mentions)
Правая панель: тренд одного топика возвратов (только одна серия — нет split)

% Mentions здесь = % возвращённых товаров с этой причиной
ВАЖНО: возврат > негативный отзыв по серьёзности

{
  "screen_type": "returns_insights_and_trend",
  "return_topics": [
    {
      "topic": "<>",
      "return_mention_rate": <decimal>,
      "severity": "<critical/major/minor>",
      "cross_reference": {
        "review_mention_rate": <decimal or null>,
        "impact_value": <decimal or null>,
        "disproportion_flag": <bool>
      }
    }
  ],
  "return_trend": {
    "topic_shown": "<>",
    "data_points": [{"month": "<YYYY-MM>", "return_pct": <decimal>}],
    "trend_direction": "<>"
  }
}
```

**Правила Returns:**
- return_rate ≥15% → critical: каждый 6-й или чаще возврат
- return_rate 5–15% → major
- return_rate > review_rate × 2 → ⚠️ скрытая проблема: люди молча возвращают без отзыва
- "Advertised Vs Actual Product" >5% → ⚠️ листинг обещает больше чем товар даёт
- Size/Comfort returns → проверить применимость к конкретному типу товара

### 2.9 Top Niche Insights AI Text Report (.txt / .docx)
```
ИСТОЧНИК: AI-генерированный Amazon. Вторичный. Использовать как контекст,
приоритет у CSV и скриншотов при конфликте.

Разделы: Niche Overview | Top Product Features | Customer Reviews |
         Customer Demographics | Search Terms | Pricing

{
  "source_type": "ai_text_report",
  "confidence": "secondary",
  "overview": {
    "revenue_range_360d": {"min": <>, "max": <>},
    "search_volume_360d": <int>,
    "search_volume_growth_yoy": <decimal>,
    "conversion_rate": <decimal>,
    "brand_count_growth_yoy": <decimal>,
    "successful_launches_past_year": <int>
  },
  "seasonality": {
    "peaks": [{"period": "<>", "search_volume_approx": <int>}],
    "lows": [{"period": "<>", "search_volume_approx": <int>}]
  },
  "product_features": {
    "top_features": [],
    "top_combinations": [],
    "format_distribution": [],
    "emerging_trends": []
  },
  "demographics": {
    "primary_gender": "<>",
    "primary_age_range": "<>",
    "income_level": "<>",
    "segments": []
  },
  "search_terms": {
    "fast_growing": [{"term": "<>", "growth_yoy": <decimal>}],
    "high_converting": [{"term": "<>", "conversion_rate": <decimal>}]
  },
  "pricing": {
    "segments": [],
    "sweet_spot": {"min": <>, "max": <>, "rationale": "<>"}
  },
  "cross_reference_flags": []
}
Правила: % → decimal | "+" суффиксы → это нижняя граница | расплывчатые значения → null + notes
```

---

## БЛОК 3 — Кросс-референс Engine

После извлечения всех источников выполни сопоставление:

```
ПОЛЯ ДЛЯ КРОСС-РЕФЕРЕНСА:

| Поле | CSV Products | CSV Search Terms | Competition Table | Niche Overview | AI Text |
|---|---|---|---|---|---|
| Search Volume 360d | — | total_volume | search_volume.360d | search_volume_360d | overview.search_volume |
| Avg Price | avg_price_all | — | avg_selling_price.360d | avg_price_360d | pricing.sweet_spot |
| Brand Count | unique_brands | — | brand_count.today | — | overview.brand_count |
| Top 5 Click Share | top5_click_share | — | top5_products.today | — | competition.top5 |
| Conversion Rate | — | avg by cluster | search_conversion.today | — | overview.conversion |

ДЛЯ КАЖДОГО ПОЛЯ:
- Значения совпадают (разница <5%) → confirmed: true, confidence: "high"
- Значения расходятся (>5%) → conflict: true, note: "<объяснение>"
  Типичные объяснения: разные временные окна | разная методология расчёта | AI-округление
- Приоритет при конфликте: CSV > скриншот > AI text
```

---

## БЛОК 4 — Финальный Синтез

После обработки всех источников сформируй финальный анализ:

```
{
  "niche_analysis": {
    "niche_name": "<>",
    "analysis_date": "<>",
    "data_sources_used": ["<список источников>"],
    "data_completeness": "<high/medium/low>",

    "market_overview": {
      "search_volume_360d": <int, приоритет CSV/скриншот>,
      "search_volume_trend": "<growing/seasonal/declining>",
      "avg_price": <decimal>,
      "price_trend": "<rising/stable/falling>",
      "revenue_estimate": "<диапазон если доступен>",
      "seasonality": "<описание пиков и спадов>",
      "market_maturity": "<emerging/growing/mature/declining>"
    },

    "competition_assessment": {
      "entry_difficulty": "<low/medium/high>",
      "market_concentration": "<fragmented/moderate/concentrated>",
      "top5_click_share": <decimal>,
      "brand_count": <int>,
      "avg_review_count": <int>,
      "review_barrier": "<low/medium/high>",
      "avg_rating": <decimal>,
      "rating_signal": "<opportunity/neutral/strong_incumbents>",
      "ppc_dependency": "<low/medium/high>",
      "out_of_stock_rate": <decimal>,
      "supply_signal": "<healthy/strained/critical>",
      "price_premiumization": "<bool>",
      "summary": "<2-3 предложения>"
    },

    "demand_signals": {
      "conversion_rate_current": <decimal>,
      "market_satisfaction": "<unsatisfied/neutral/satisfied>",
      "search_trends": {
        "exploding_clusters": [],
        "declining_clusters": [],
        "high_intent_terms": []
      },
      "true_addressable_market": "<% прямых конкурентов от общего трафика>",
      "different_product_types_in_niche": ["<тип1>", "<тип2>"]
    },

    "product_insights": {
      "winning_features": ["<фича1>", "<фича2>"],
      "winning_combinations": ["<комбо1>"],
      "format_distribution": [],
      "emerging_subcategories": [],
      "price_sweet_spot": {"min": <>, "max": <>, "rationale": "<>"}
    },

    "customer_insights": {
      "primary_demographic": "<описание>",
      "top_positive_drivers": [],
      "top_negative_drivers": [],
      "main_return_reasons": [],
      "quality_gap": "<описание незакрытых потребностей>",
      "listing_risk_factors": []
    },

    "confirmed_facts": [
      {
        "fact": "<утверждение>",
        "sources": ["<источник1>", "<источник2>"],
        "values": {"source1": "<значение>", "source2": "<значение>"}
      }
    ],

    "flags_for_investigation": [
      {
        "flag": "<наблюдение>",
        "source": "<один источник>",
        "needs": "<что нужно для подтверждения>"
      }
    ],

    "conflicts": [
      {
        "field": "<поле>",
        "values": {"source1": "<>", "source2": "<>"},
        "resolution": "<приоритетное значение и почему>"
      }
    ],

    "opportunity_signals": [
      {
        "signal": "<описание возможности>",
        "evidence": ["<источник + данные>"],
        "confidence": "<high/medium/low>",
        "type": "<supply_gap/demand_gap/product_gap/listing_gap/segment_gap>"
      }
    ],

    "key_risks": [
      {
        "risk": "<описание риска>",
        "evidence": ["<источник + данные>"],
        "severity": "<high/medium/low>"
      }
    ]
  }
}
```

---

## БЛОК 5 — Правила финальных выводов

### Что можно утверждать твёрдо (✅)
Только при подтверждении ≥2 независимыми источниками:
- "Durability — главная проблема качества" → Reviews 9.95% + Impact -0.09★ + Trend хронически высокий
- "Рынок открывается" → Top 5 click share падает в Competition Table + подтверждается в Products CSV
- "Out-of-stock — критический" → Competition Table сегодня + данные о возвратах

### Что формулировать как сигнал (⚠️)
При наличии одного источника или косвенных данных:
- Ценовые стратегии
- PPC рекомендации (нужна информация о CPC)
- Прогнозы сезонности
- Выводы о конкретных SKU

### Что НЕ делать
- Не давать рекомендации по ценообразованию без данных о маржинальности
- Не утверждать "дорогой/дешёвый трафик" без данных о CPC
- Не делать выводы о подходящем продукте только на основе трендов запросов
- Не интерпретировать данные AI text report как факт без подтверждения из CSV/скриншотов

---

## БЛОК 6 — Формат вывода

Итоговый анализ представить в следующей структуре:

### 1. Краткое резюме (Executive Summary)
3–5 предложений: что за ниша, основная возможность, главный риск.

### 2. Рыночная картина
- Объём и тренд спроса (с источниками)
- Сезонность
- Ценовой диапазон и тренд

### 3. Конкурентный анализ
- Концентрация рынка
- Барьеры входа (отзывы, рейтинг, PPC)
- Состояние запасов
- Кто лидеры и почему

### 4. Спрос и поисковые паттерны
- Кластеры запросов
- Растущие и падающие тренды
- Незакрытый интент
- Испаноязычный сегмент (если значим)

### 5. Продуктовый анализ
- Выигрышные фичи и комбинации
- Форматы и ценовые сегменты
- Разные типы товаров в нише

### 6. Голос покупателя
- Что ценят (позитивные драйверы)
- Что не нравится (негативные драйверы)
- Причины возвратов
- Что лидеры делают лучше

### 7. Подтверждённые факты ✅
Список фактов с 2+ источниками.

### 8. Сигналы для изучения ⚠️
Наблюдения из одного источника, требующие проверки.

### 9. Конфликты данных ⚡
Расхождения между источниками с объяснением.

### 10. Возможности и риски
Структурированный список с уровнем уверенности.

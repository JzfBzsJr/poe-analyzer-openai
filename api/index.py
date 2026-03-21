import os
import sys
from datetime import datetime

from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv

load_dotenv()

# Add api/ to path so relative imports work in Vercel
sys.path.insert(0, os.path.dirname(__file__))

from parsers.file_classifier import classify
from parsers.csv_parser import parse_products_csv, parse_search_terms_csv
from parsers.image_parser import parse_images
from parsers.text_parser import parse_chrome_ext, parse_ai_text_report
from analysis.cross_reference import cross_reference
from analysis.synthesizer import synthesize
from report.html_formatter import build_html

app = Flask(__name__, static_folder="../static")


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    files = request.files.getlist("files[]")
    if not files:
        # Legacy single-file support
        f = request.files.get("file")
        if f:
            files = [f]

    api_key = request.form.get("api_key", "").strip()
    if not api_key:
        return jsonify({"error": "API ключ не указан"}), 400

    if not files:
        return jsonify({"error": "Файлы не загружены"}), 400

    # ── Step 1: Classify each file ─────────────────────────────────────────────
    classified = []  # (filename, file_type, content_bytes)
    for f in files:
        if not f or not f.filename:
            continue
        content = f.read()
        ftype = classify(f.filename, content)
        classified.append((f.filename, ftype, content))

    sources_used = [fname for fname, _, _ in classified]

    # ── Step 2: Parse each source ──────────────────────────────────────────────
    schema = {}
    images_to_process = []  # (filename, bytes)

    for fname, ftype, content in classified:
        try:
            if ftype == "products_csv":
                schema["products_csv"] = parse_products_csv(content)

            elif ftype == "search_terms_csv":
                schema["search_terms_csv"] = parse_search_terms_csv(content)

            elif ftype == "image":
                images_to_process.append((fname, content, api_key))

            elif ftype == "chrome_ext_txt":
                schema["chrome_ext"] = parse_chrome_ext(content, api_key)

            elif ftype == "ai_text_report":
                schema["ai_text"] = parse_ai_text_report(content, api_key)

        except Exception as e:
            schema.setdefault("_parse_errors", []).append(f"{fname}: {str(e)}")

    # Process all images in parallel
    if images_to_process:
        try:
            image_results = parse_images(images_to_process, api_key)
            for result in image_results:
                screen_type = result.get("_screen_type") or result.get("screen_type", "")
                if screen_type == "niche_overview":
                    schema["niche_overview"] = result
                elif screen_type == "competition_table":
                    schema["competition_table"] = result
                elif screen_type == "demand_chart":
                    schema["demand_chart"] = result
                elif screen_type == "topic_impact_positive":
                    schema["topic_impact_positive"] = result
                elif screen_type == "topic_impact_negative":
                    schema["topic_impact_negative"] = result
                elif screen_type == "returns_insights":
                    schema["returns_insights"] = result
        except Exception as e:
            schema.setdefault("_parse_errors", []).append(f"images: {str(e)}")

    # ── Step 3: Extract niche name ─────────────────────────────────────────────
    niche_name = ""
    for src_key in ["niche_overview", "products_csv", "search_terms_csv", "chrome_ext", "ai_text"]:
        src = schema.get(src_key, {})
        if isinstance(src, dict):
            name = src.get("niche_name") or (src.get("overview") or {}).get("niche_name")
            if name:
                niche_name = name
                break
    schema["niche_name"] = niche_name

    # ── Step 4: Cross-reference ────────────────────────────────────────────────
    try:
        cross_ref = cross_reference(schema)
    except Exception as e:
        cross_ref = {"confirmed_facts": [], "signals": [], "conflicts": [],
                     "_error": str(e)}

    # ── Step 5: Synthesize ─────────────────────────────────────────────────────
    analysis_date = datetime.now().strftime("%d.%m.%Y")
    try:
        dashboard_data = synthesize(schema, cross_ref, api_key)
    except Exception as e:
        dashboard_data = f"## Ошибка синтеза\n\n{str(e)}"

    # ── Step 6: Build HTML dashboard ──────────────────────────────────────────
    try:
        html_report = build_html(
            dashboard_data,
            niche_name=niche_name,
            sources_used=sources_used,
            analysis_date=analysis_date,
        )
    except Exception as e:
        html_report = f"<p>Ошибка формирования дашборда: {e}</p>"

    return jsonify({
        "html": html_report,
        "niche_name": niche_name,
        "sources_used": sources_used,
        "errors": schema.get("_parse_errors", []),
    })


if __name__ == "__main__":
    app.run(debug=True)

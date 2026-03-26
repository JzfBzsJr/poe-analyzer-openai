"""
Dashboard HTML renderer — builds a rich visual dashboard from structured JSON data.
"""
import html as html_lib

_CSS = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --accent: #7c3aed;
  --orange: #f97316;
  --ink: #0d0d0d;
  --muted: #888888;
  --white: #ffffff;
}
body { font-family: 'Space Grotesk', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #ffffff; color: var(--ink); }

/* ── Cover ── */
.cover {
  background: #ffffff; display: flex; flex-direction: column;
  padding: 72px 72px 60px; border-bottom: 1px solid #e0e0e0; gap: 40px;
}
.cover-badge {
  display: inline-block; border: 1px solid #ccc; color: var(--muted);
  font-size: 11px; font-weight: 600; letter-spacing: 0.15em; text-transform: uppercase;
  padding: 6px 14px; border-radius: 2px; width: fit-content;
}
.cover-content { padding-bottom: 0; }
.cover-title {
  font-size: clamp(52px, 8vw, 96px); font-weight: 700; line-height: 1.0;
  letter-spacing: -0.02em; color: var(--ink); margin-bottom: 8px;
}
.cover-title .accent { color: var(--accent); display: block; }
.cover-subtitle { font-size: 18px; color: #666666; font-weight: 400; margin-top: 20px; max-width: 620px; line-height: 1.6; }
.cover-bar { width: 4px; height: 56px; background: var(--accent); margin-bottom: 24px; }
.cover-meta {
  display: flex; gap: 32px; padding-top: 32px; border-top: 1px solid #e0e0e0;
  font-size: 12px; color: var(--muted); font-weight: 500; letter-spacing: 0.05em; text-transform: uppercase;
}

/* ── TOC ── */
.toc { background: #ffffff; padding: 72px; border-bottom: 1px solid #e0e0e0; }
.section-label { font-size: 11px; font-weight: 600; letter-spacing: 0.2em; text-transform: uppercase; color: var(--muted); margin-bottom: 24px; }
.toc-heading { font-size: 48px; font-weight: 700; line-height: 1.1; margin-bottom: 48px; color: var(--ink); }
.toc-heading .accent { color: var(--accent); }
.toc-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0; }
.toc-item {
  display: flex; align-items: flex-start; gap: 16px;
  padding: 20px 0; border-bottom: 1px solid #e0e0e0;
}
.toc-item:nth-child(odd)  { padding-right: 40px; border-right: 1px solid #e0e0e0; }
.toc-item:nth-child(even) { padding-left: 40px; }
.toc-num { font-size: 12px; font-weight: 700; color: var(--accent); letter-spacing: 0.1em; min-width: 28px; padding-top: 3px; }
.toc-text { font-size: 20px; font-weight: 600; color: var(--ink); line-height: 1.4; }

/* ── Content sections ── */
.content-section { background: var(--orange); padding: 72px; border-bottom: 4px solid var(--ink); }
.content-section .section-label { color: rgba(255,255,255,0.6); }
.section-heading { font-size: clamp(28px, 4vw, 44px); font-weight: 700; color: #ffffff; line-height: 1.2; margin-bottom: 40px; }
.section-heading mark { background: var(--accent); color: #ffffff; padding: 2px 8px; border-radius: 2px; }
.section-intro { font-size: 21px; color: rgba(255,255,255,0.85); line-height: 1.7; max-width: 760px; margin-bottom: 40px; }

/* ── Cards ── */
.card-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.card { background: #ffffff; border-radius: 4px; padding: 24px; border-top: 4px solid var(--ink); }
.card.dark    { background: #1a1a1a; border-top-color: var(--accent); color: #ffffff; }
.card.dark .card-title { color: #ffffff; }
.card.dark .card-body  { color: rgba(255,255,255,0.8); }
.card.warning { border-top-color: #ef4444; }
.card.success { border-top-color: #22c55e; }
.card-icon  { font-size: 24px; margin-bottom: 12px; }
.card-title { font-size: 20px; font-weight: 700; margin-bottom: 10px; color: var(--ink); }
.card-body  { font-size: 17px; line-height: 1.6; color: #444; }

/* ── Highlight boxes ── */
.highlight-box {
  border-left: 4px solid var(--accent); background: rgba(124,58,237,0.15);
  padding: 20px 24px; border-radius: 0 4px 4px 0; margin: 24px 0;
}
.highlight-box.red    { border-left-color: #e05a2b; background: rgba(224,90,43,0.15); }
.highlight-box.green  { border-left-color: #ffffff; background: rgba(255,255,255,0.15); }
.highlight-box.yellow { border-left-color: #fbbf24; background: rgba(251,191,36,0.15); }
.highlight-box.accent { border-left-color: var(--accent); background: rgba(124,58,237,0.2); }
.highlight-box-label { font-size: 12px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: #ffffff; margin-bottom: 8px; }
.highlight-box-text  { font-size: 17px; color: rgba(255,255,255,0.9); line-height: 1.6; }

/* ── Conclusion ── */
.conclusion { background: #ffffff; padding: 72px; }
.priority-card {
  display: grid; grid-template-columns: 80px 1fr; border: 1px solid #e0e0e0;
  border-radius: 4px; margin-bottom: 16px; overflow: hidden;
}
.priority-num {
  background: var(--accent); display: flex; align-items: center; justify-content: center;
  font-size: 36px; font-weight: 700; color: #ffffff;
}
.priority-content { padding: 20px 24px; }
.priority-title { font-size: 17px; font-weight: 700; color: var(--ink); margin-bottom: 8px; }
.priority-text  { font-size: 15px; color: #666; line-height: 1.6; }

@media (max-width: 900px) {
  .cover, .toc, .content-section, .conclusion { padding: 40px 32px; }
  .card-grid { grid-template-columns: repeat(2, 1fr); }
  .toc-grid  { grid-template-columns: 1fr; }
  .toc-item:nth-child(odd)  { border-right: none; padding-right: 0; }
  .toc-item:nth-child(even) { padding-left: 0; }
}
@media (max-width: 600px) {
  .card-grid { grid-template-columns: 1fr; }
  .cover-title { font-size: 40px; }
}
"""

_GOOGLE_FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">'
)


def _e(text) -> str:
    """HTML-escape a value."""
    if text is None:
        return ""
    return html_lib.escape(str(text))


def _render_card(card: dict) -> str:
    variant = card.get("variant", "")
    cls = f"card {variant}".strip() if variant else "card"
    return (
        f'<div class="{cls}">'
        f'<div class="card-icon">{_e(card.get("icon",""))}</div>'
        f'<div class="card-title">{_e(card.get("title",""))}</div>'
        f'<div class="card-body">{_e(card.get("body",""))}</div>'
        f"</div>"
    )


def _render_highlight(hl: dict) -> str:
    if not hl:
        return ""
    variant = hl.get("variant", "")
    cls = f"highlight-box {variant}".strip() if variant else "highlight-box"
    return (
        f'<div class="{cls}">'
        f'<div class="highlight-box-label">{_e(hl.get("label",""))}</div>'
        f'<div class="highlight-box-text">{_e(hl.get("text",""))}</div>'
        f"</div>"
    )


def _render_section(section: dict) -> str:
    label = _e(section.get("label", ""))
    heading = section.get("heading", "")
    # First word plain, rest in <mark>
    words = heading.split(None, 1)
    if len(words) == 2:
        heading_html = f"{_e(words[0])} <mark>{_e(words[1])}</mark>"
    else:
        heading_html = _e(heading)

    intro = _e(section.get("intro", ""))
    cards_html = "".join(_render_card(c) for c in section.get("cards", []))
    highlight_html = _render_highlight(section.get("highlight"))

    return (
        f'<section class="content-section">'
        f'<p class="section-label">{label}</p>'
        f'<h2 class="section-heading">{heading_html}</h2>'
        f'<p class="section-intro">{intro}</p>'
        f'<div class="card-grid">{cards_html}</div>'
        f"{highlight_html}"
        f"</section>"
    )


def _render_toc(sections: list) -> str:
    items = ""
    for s in sections:
        raw_label = s.get("label", "")
        num = _e(raw_label.replace("Раздел ", "").strip())
        text = _e(s.get("heading", ""))
        items += (
            f'<div class="toc-item">'
            f'<span class="toc-num">{num}</span>'
            f'<div><div class="toc-text">{text}</div></div>'
            f"</div>"
        )
    return (
        '<section class="toc">'
        '<p class="section-label">Навигация</p>'
        '<h2 class="toc-heading">Содержание <span class="accent">анализа</span></h2>'
        f'<div class="toc-grid">{items}</div>'
        "</section>"
    )


def _render_priorities(priorities: list) -> str:
    items = ""
    for p in priorities:
        items += (
            '<div class="priority-card">'
            f'<div class="priority-num">#{_e(p.get("num",""))}</div>'
            '<div class="priority-content">'
            f'<div class="priority-title">{_e(p.get("title",""))}</div>'
            f'<div class="priority-text">{_e(p.get("text",""))}</div>'
            "</div></div>"
        )
    return (
        '<section class="conclusion">'
        '<p class="section-label" style="color: var(--muted)">Заключение</p>'
        '<h2 class="toc-heading" style="margin-bottom: 32px;">Топ <span class="accent">приоритетов</span></h2>'
        f"{items}"
        "</section>"
    )


def build_html(
    dashboard_data,
    niche_name: str = "",
    sources_used: list = None,
    analysis_date: str = "",
) -> str:
    """
    dashboard_data: dict returned by synthesizer.synthesize(), or str fallback
    Returns: full HTML string for the dashboard
    """
    if sources_used is None:
        sources_used = []

    # Fallback if synthesis failed and returned a string (e.g. error message)
    if isinstance(dashboard_data, str):
        return _fallback_html(dashboard_data, niche_name, analysis_date)

    cover_subtitle = dashboard_data.get("cover_subtitle", "")
    sections = dashboard_data.get("sections", [])
    priorities = dashboard_data.get("priorities", [])

    # Split niche name: first word black, rest accent
    niche_words = (niche_name or "POE Analysis").split(None, 1)
    niche_line1 = _e(niche_words[0])
    niche_line2 = _e(niche_words[1]) if len(niche_words) > 1 else ""

    sources_count = len(sources_used)
    sources_list = ", ".join(sources_used) if sources_used else "—"

    toc_html = _render_toc(sections)
    sections_html = "".join(_render_section(s) for s in sections)
    priorities_html = _render_priorities(priorities) if priorities else ""

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_e(niche_name)} — POE Niche Analysis</title>
{_GOOGLE_FONTS}
<style>{_CSS}</style>
</head>
<body>

<section class="cover">
  <div class="cover-badge">Amazon Product Opportunity Explorer</div>
  <div class="cover-content">
    <div class="cover-bar"></div>
    <h1 class="cover-title">
      {niche_line1}
      <span class="accent">{niche_line2}</span>
    </h1>
    <p class="cover-subtitle">{_e(cover_subtitle)}</p>
  </div>
  <div class="cover-meta">
    <span>POE Analysis Brain</span>
    <span>{_e(analysis_date)}</span>
    <span>{sources_count} источников данных</span>
  </div>
</section>

{toc_html}
{sections_html}
{priorities_html}

<script>
(function(){{
  function walk(node){{
    if(node.nodeType===3){{
      node.textContent=node.textContent.replace(/\b(\d{{5,}})\b/g,function(m){{return Number(m).toLocaleString('de-DE');}});
    }}else{{
      for(var i=0;i<node.childNodes.length;i++)walk(node.childNodes[i]);
    }}
  }}
  walk(document.body);
}})();
</script>
</body>
</html>"""


def _fallback_html(text: str, niche_name: str, analysis_date: str) -> str:
    """Fallback when synthesis JSON parsing failed — show raw text in styled page."""
    escaped = _e(text)
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>{_e(niche_name)} — POE Analysis</title>
{_GOOGLE_FONTS}
<style>
  body {{ font-family: 'Space Grotesk', sans-serif; padding: 48px 72px; max-width: 900px; margin: 0 auto; }}
  h1 {{ font-size: 36px; margin-bottom: 24px; }}
  pre {{ white-space: pre-wrap; font-size: 15px; line-height: 1.7; background: #f5f5f5; padding: 24px; border-radius: 8px; }}
</style>
</head>
<body>
<h1>{_e(niche_name)} — Анализ ниши</h1>
<p style="color:#888;margin-bottom:24px;">{_e(analysis_date)}</p>
<pre>{escaped}</pre>
</body>
</html>"""

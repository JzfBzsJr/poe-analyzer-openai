"""
Image parser — sends screenshots to Claude Vision with per-type prompts.
Processes all images in parallel using ThreadPoolExecutor.
"""
import base64
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

import openai

from prompts.extraction import (
    PROMPT_IDENTIFY_IMAGE,
    PROMPT_NICHE_OVERVIEW,
    PROMPT_COMPETITION_TABLE,
    PROMPT_DEMAND_CHART,
    PROMPT_TOPIC_IMPACT,
    PROMPT_RETURNS,
)

def _get_client(api_key: str):
    return openai.OpenAI(api_key=api_key)


def _b64(image_bytes: bytes) -> str:
    return base64.standard_b64encode(image_bytes).decode("utf-8")


def _media_type(filename: str) -> str:
    name = filename.lower()
    if name.endswith(".png"):
        return "image/png"
    if name.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    if name.endswith(".webp"):
        return "image/webp"
    return "image/png"


def _call_claude(prompt: str, image_bytes: bytes, filename: str, api_key: str) -> str:
    """Single Vision API call. Returns raw text."""
    client = _get_client(api_key)
    response = client.chat.completions.create(
        model="gpt-5.4",
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:{_media_type(filename)};base64,{_b64(image_bytes)}"}},
                {"type": "text", "text": prompt},
            ],
        }],
    )
    return response.choices[0].message.content.strip()


def _identify_image(image_bytes: bytes, filename: str, api_key: str) -> str:
    """Ask Claude what type of POE screenshot this is."""
    result = _call_claude(PROMPT_IDENTIFY_IMAGE, image_bytes, filename, api_key)
    known = {
        "niche_overview", "competition_table", "demand_chart",
        "topic_impact_positive", "topic_impact_negative",
        "returns_insights", "unknown",
    }
    cleaned = result.strip().lower().replace('"', "").replace("'", "")
    return cleaned if cleaned in known else "unknown"


def _extract_json(text: str) -> dict:
    """Extract JSON from Claude response, handling markdown code blocks."""
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Strip markdown code blocks
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass
    # Last resort: find first { ... }
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return {}


def _process_single_image(filename: str, image_bytes: bytes, api_key: str) -> dict:
    """Identify type then extract data from one screenshot."""
    screen_type = _identify_image(image_bytes, filename, api_key)

    if screen_type == "niche_overview":
        raw = _call_claude(PROMPT_NICHE_OVERVIEW, image_bytes, filename, api_key)
    elif screen_type == "competition_table":
        raw = _call_claude(PROMPT_COMPETITION_TABLE, image_bytes, filename, api_key)
    elif screen_type == "demand_chart":
        raw = _call_claude(PROMPT_DEMAND_CHART, image_bytes, filename, api_key)
    elif screen_type == "topic_impact_positive":
        prompt = PROMPT_TOPIC_IMPACT.replace("{tab}", "positive_topics")
        raw = _call_claude(prompt, image_bytes, filename, api_key)
    elif screen_type == "topic_impact_negative":
        prompt = PROMPT_TOPIC_IMPACT.replace("{tab}", "negative_topics")
        raw = _call_claude(prompt, image_bytes, filename, api_key)
    elif screen_type == "returns_insights":
        raw = _call_claude(PROMPT_RETURNS, image_bytes, filename, api_key)
    else:
        return {"screen_type": "unknown", "filename": filename}

    data = _extract_json(raw)
    data["_filename"] = filename
    data["_screen_type"] = screen_type
    return data


def parse_images(images: list, api_key: str) -> list:
    """
    Parse multiple screenshots in parallel.
    images: list of (filename: str, image_bytes: bytes, api_key: str)
    Returns: list of extracted dicts
    """
    if not images:
        return []

    results = []
    with ThreadPoolExecutor(max_workers=min(len(images), 5)) as executor:
        futures = {
            executor.submit(_process_single_image, fname, data, api_key): fname
            for fname, data, _ in images
        }
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as e:
                fname = futures[future]
                results.append({
                    "screen_type": "error",
                    "_filename": fname,
                    "_error": str(e),
                })

    return results

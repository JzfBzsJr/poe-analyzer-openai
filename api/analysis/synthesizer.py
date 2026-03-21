"""
Final synthesis — two parallel API calls (A: cover + sections 1-4, B: sections 5-8 + priorities).
Each response is ~8-10K chars, eliminating JSON syntax errors from long single-call outputs.
"""
import json
import re
from concurrent.futures import ThreadPoolExecutor

import openai

from prompts.synthesis import PROMPT_SYNTHESIS_A, PROMPT_SYNTHESIS_B


def _get_client(api_key: str):
    return openai.OpenAI(api_key=api_key)


def _sanitize_json(text: str) -> str:
    """Fix common JSON issues: strip markdown, trailing commas, literal control chars in strings."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text).strip()
    text = re.sub(r",\s*([\]}])", r"\1", text)

    # Escape literal newlines/tabs inside string values
    result = []
    in_string = False
    i = 0
    while i < len(text):
        c = text[i]
        if c == '\\' and in_string and i + 1 < len(text):
            result.append(c)
            result.append(text[i + 1])
            i += 2
            continue
        if c == '"':
            in_string = not in_string
            result.append(c)
            i += 1
            continue
        if in_string:
            if c == '\n':
                result.append('\\n')
                i += 1
                continue
            if c == '\r':
                result.append('\\r')
                i += 1
                continue
            if c == '\t':
                result.append('\\t')
                i += 1
                continue
        result.append(c)
        i += 1
    return ''.join(result)


def _extract_json(text: str) -> dict:
    """Extract JSON from Claude response with multiple fallback strategies."""
    text = _sanitize_json(text)

    # 1. Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Find outermost {...} and re-sanitize
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        candidate = _sanitize_json(match.group(0))
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # 3. Close truncated JSON
    try:
        base = match.group(0) if match else text
        fixed = base
        fixed = re.sub(r',\s*"[^"]*"\s*:\s*[^,}\]]*$', "", fixed)
        fixed = re.sub(r',\s*\{[^}]*$', "", fixed)
        open_b  = fixed.count("{") - fixed.count("}")
        open_sq = fixed.count("[") - fixed.count("]")
        fixed += "]" * max(0, open_sq) + "}" * max(0, open_b)
        fixed = re.sub(r",\s*([\]}])", r"\1", fixed)
        return json.loads(fixed)
    except Exception:
        pass

    raise ValueError(f"Could not parse JSON (len={len(text)}, preview={text[:300]!r})")


def _call_claude(prompt: str, api_key: str) -> dict:
    """Single LLM API call → parsed dict."""
    client = _get_client(api_key)
    response = client.chat.completions.create(
        model="gpt-5.4",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return _extract_json(response.choices[0].message.content.strip())


def synthesize(schema: dict, cross_ref: dict, api_key: str) -> dict:
    """
    Two parallel Claude calls:
      A → cover_subtitle + sections 1-4
      B → sections 5-8 + priorities
    Returns merged dict for the dashboard.
    """
    schema_json = json.dumps(schema, ensure_ascii=False, separators=(",", ":"), default=str)
    cross_ref_json = json.dumps(cross_ref, ensure_ascii=False, separators=(",", ":"), default=str)

    # Truncate schema if too large
    if len(schema_json) > 20000:
        trimmed = dict(schema)
        if "products_csv" in trimmed and isinstance(trimmed["products_csv"], dict):
            pc = dict(trimmed["products_csv"])
            if "products" in pc:
                pc["products"] = pc["products"][:20]
                pc["_note"] = f"Trimmed to 20 of {schema.get('products_csv', {}).get('total_products', '?')}"
            trimmed["products_csv"] = pc
        schema_json = json.dumps(trimmed, ensure_ascii=False, separators=(",", ":"), default=str)

    prompt_a = PROMPT_SYNTHESIS_A.format(unified_schema=schema_json, cross_ref=cross_ref_json)
    prompt_b = PROMPT_SYNTHESIS_B.format(unified_schema=schema_json, cross_ref=cross_ref_json)

    result_a, result_b = {}, {}
    error_a, error_b = None, None

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_a = executor.submit(_call_claude, prompt_a, api_key)
        future_b = executor.submit(_call_claude, prompt_b, api_key)
        try:
            result_a = future_a.result()
        except Exception as e:
            error_a = str(e)
        try:
            result_b = future_b.result()
        except Exception as e:
            error_b = str(e)

    # If both calls failed, raise so the user sees the actual error
    if error_a and error_b:
        raise ValueError(f"Both synthesis calls failed.\nPart A: {error_a}\nPart B: {error_b}")

    return {
        "cover_subtitle": result_a.get("cover_subtitle", ""),
        "sections": result_a.get("sections", []) + result_b.get("sections", []),
        "priorities": result_b.get("priorities", []),
        "_synthesis_errors": [e for e in [error_a, error_b] if e],
    }

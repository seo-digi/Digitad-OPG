"""Claude API calls for mapping validation and SEO tag rewriting."""
import json
import re
import anthropic


def _extract_json(text):
    """Extract JSON array from response text, handling markdown code blocks."""
    # Try direct parse first
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try extracting from ```json ... ``` blocks
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if match:
        return json.loads(match.group(1).strip())
    # Try finding the JSON array directly
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    raise ValueError(f"Could not extract JSON from response: {text[:200]}")
from config import (
    SEO_SYSTEM_PROMPT, MAPPING_VALIDATION_PROMPT,
    MAX_PAGES_PER_BATCH, META_DESC_MIN_LENGTH, META_DESC_MAX_LENGTH,
)


def validate_meta_desc_length(desc):
    """Check if meta description is within acceptable range."""
    return META_DESC_MIN_LENGTH <= len(desc) <= META_DESC_MAX_LENGTH


def build_rewrite_payload(pages, brand_name, language):
    """Build the user prompt for tag rewriting."""
    lang_label = "French (FR-CA)" if language == "fr" else "English (EN)"
    lines = [
        f"Brand name: {brand_name}",
        f"Language: {lang_label}",
        "",
        "Pages to optimize:",
        "",
    ]
    for p in pages:
        lines.append(f"URL: {p['url']}")
        lines.append(f"Target keyword: {p['keyword']}")
        lines.append(f"Page type: {p['page_type']}")
        lines.append(f"Current title: {p['current_title']}")
        lines.append(f"Current H1: {p['current_h1']}")
        lines.append(f"Current meta description: {p['current_meta_desc']}")
        lines.append("")

    return "\n".join(lines)


def validate_mapping(mappings, client=None, model="claude-haiku-4-5-20251001"):
    """Send mappings to Claude for semantic validation."""
    if client is None:
        client = anthropic.Anthropic()

    lines = []
    for m in mappings:
        queries_str = ", ".join(
            f"{q['query']} ({q['impressions']} imp)"
            for q in m["top_queries"][:3]
        )
        lines.append(f"URL: {m['url']} | Keyword: {m['keyword']} | Top GSC: {queries_str}")

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=MAPPING_VALIDATION_PROMPT,
        messages=[{"role": "user", "content": "\n".join(lines)}],
    )

    return _extract_json(response.content[0].text)


def rewrite_tags(pages, brand_name, language, client=None,
                 model="claude-sonnet-4-20250514", on_batch_complete=None):
    """Rewrite SEO tags using Claude API.

    Args:
        on_batch_complete: Optional callback(completed_count, total) called after each batch.
    """
    if client is None:
        client = anthropic.Anthropic()

    all_results = []

    for i in range(0, len(pages), MAX_PAGES_PER_BATCH):
        batch = pages[i:i + MAX_PAGES_PER_BATCH]
        prompt = build_rewrite_payload(batch, brand_name, language)

        system = SEO_SYSTEM_PROMPT.format(brand_name=brand_name)
        response = client.messages.create(
            model=model,
            max_tokens=8192,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )

        batch_results = _extract_json(response.content[0].text)
        all_results.extend(batch_results)

        if on_batch_complete:
            on_batch_complete(len(all_results), len(pages))

    return all_results

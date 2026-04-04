"""Client configuration and constants for the optimization plan generator."""

# Known column header labels for auto-detection (FR and EN variants)
KEYWORD_COLUMN_LABELS = [
    "mots-clés clusters opportunités",
    "cluster keywords",
    "mot-clé",
    "keyword",
    "mots-clés",
]

VOLUME_COLUMN_LABELS = [
    "volume de recherche mensuel",
    "search volume",
    "volume",
]

POSITION_COLUMN_LABELS = [
    "position actuelle",
    "current position",
    "position",
]

PRIORITY_COLUMN_LABELS = [
    "priorité stratégique",
    "priorite strategique",
    "strategic priority",
    "priority",
]

URL_COLUMN_LABELS = [
    "url positionnée",
    "url positionnee",
    "ranked url",
    "url",
]

INTENT_COLUMN_LABELS = [
    "intention de recherche",
    "search intent",
    "intention",
    "intent",
]

# Default Excel layout
DEFAULT_HEADER_ROW = 4  # 1-indexed (row 4 in Excel = index 3 in openpyxl)
DEFAULT_DATA_START_ROW = 5  # 1-indexed

# Embedding model
EMBEDDING_MODEL = "intfloat/multilingual-e5-small"
SIMILARITY_THRESHOLD = 0.5  # Below this = low-confidence mapping

# Scraper
SCRAPER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
SCRAPER_RATE_LIMIT = 1.0  # seconds between requests
SCRAPER_TIMEOUT = 10  # seconds

# Rewriter
MAX_PAGES_PER_BATCH = 10  # Smaller batches for granular progress updates
MAX_REGEN_ATTEMPTS = 3
META_DESC_MIN_LENGTH = 145
META_DESC_MAX_LENGTH = 155

# SEO rewriting system prompt
SEO_SYSTEM_PROMPT = """You are an SEO specialist. Generate optimized meta titles, H1 tags, and meta descriptions for web pages.

## Meta title rules
- Always begin with the target keyword
- Less than 65 characters including "- {brand_name}"
- End with "- {brand_name}"
- Never use pipes (|). Use a colon (:) to separate keyword from conversion element
- No semantic redundancy: conversion element must not repeat words from the keyword
- EN content: Title Case
- FR content: Sentence case. Space before colon, capitalize after colon

## H1 rules
- Target keyword, lightly modified for natural reading
- No brand name suffix
- Concise

## Meta description rules
- Target 145-155 characters exactly
- Always start with a verb (action-oriented)
- Tailor to the page type

## Output format
Return a JSON array. Each element:
{{"url": "...", "new_title": "...", "new_h1": "...", "new_meta_desc": "..."}}
"""

# Mapping validation prompt
MAPPING_VALIDATION_PROMPT = """You are an SEO specialist. Review these URL-to-keyword mappings for semantic coherence.

For each mapping, check:
1. Does the keyword match the page's likely topic (based on URL structure)?
2. Is the keyword the best choice from the top GSC queries?

Return a JSON array. Each element:
{{"url": "...", "keyword": "...", "status": "OK" or "REVIEW", "suggestion": "..." or null, "reason": "..." or null}}
"""


def build_client_config(brand_name, languages, en_url_pattern="/en/",
                        model_validation="claude-haiku-4-5-20251001",
                        model_rewriting="claude-sonnet-4-20250514"):
    """Build a client configuration dict."""
    return {
        "brand_name": brand_name,
        "languages": languages,
        "en_url_pattern": en_url_pattern,
        "model_validation": model_validation,
        "model_rewriting": model_rewriting,
    }

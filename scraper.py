"""Scrape current title, H1, and meta description from URLs."""
import time
import requests
from bs4 import BeautifulSoup
from config import SCRAPER_USER_AGENT, SCRAPER_RATE_LIMIT, SCRAPER_TIMEOUT


def parse_tags_from_html(html):
    """Extract title, h1, and meta description from HTML string."""
    soup = BeautifulSoup(html, "html.parser")

    title = ""
    title_tag = soup.find("title")
    if title_tag and title_tag.string:
        title = title_tag.string.strip()

    h1 = ""
    h1_tag = soup.find("h1")
    if h1_tag:
        h1 = h1_tag.get_text(strip=True)

    meta_desc = ""
    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag and meta_tag.get("content"):
        meta_desc = meta_tag["content"].strip()

    return {"title": title, "h1": h1, "meta_description": meta_desc}


def scrape_tags(urls, rate_limit=SCRAPER_RATE_LIMIT):
    """Scrape title, H1, meta description from a list of URLs."""
    headers = {"User-Agent": SCRAPER_USER_AGENT}
    results = {}

    for i, url in enumerate(urls):
        if i > 0:
            time.sleep(rate_limit)
        try:
            resp = requests.get(url, headers=headers, timeout=SCRAPER_TIMEOUT)
            resp.raise_for_status()
            tags = parse_tags_from_html(resp.text)
            results[url] = tags
        except Exception as e:
            results[url] = {
                "title": "", "h1": "", "meta_description": "",
                "error": str(e),
            }

    return results

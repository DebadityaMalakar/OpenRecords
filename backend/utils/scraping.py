"""
Web scraping utilities for OpenRecords.
Fetches, parses, and sanitizes web pages for RAG ingestion.
"""
from __future__ import annotations

import ipaddress
import logging
import re
import unicodedata
from typing import Optional
from urllib.parse import urlparse

import bleach
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

USER_AGENT = "OpenRecordsBot/1.0 (+https://openrecords.local)"
MAX_REDIRECTS = 3
REQUEST_TIMEOUT = 10.0
MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB
MAX_TOKENS_PER_LINK = 50_000

# Tags to extract content from (in priority order)
CONTENT_TAGS = ["article", "main", "section", "div[role='main']"]

# Tags to remove
REMOVE_TAGS = [
    "nav", "footer", "header", "aside", "script", "style", "noscript",
    "iframe", "form", "button", "input", "select", "textarea",
    "svg", "canvas", "video", "audio", "img",
]


def _is_private_ip(hostname: str) -> bool:
    """Check if a hostname resolves to a private/loopback IP. SSRF protection."""
    try:
        ip = ipaddress.ip_address(hostname)
        return ip.is_private or ip.is_loopback or ip.is_reserved
    except ValueError:
        # Not an IP literal; check common private hostnames
        lower = hostname.lower()
        return lower in ("localhost", "127.0.0.1", "0.0.0.0", "::1")


def validate_url(url: str) -> tuple[bool, str]:
    """
    Validate a URL for safety.
    Returns (is_valid, error_message).
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Invalid URL format"

    if parsed.scheme not in ("http", "https"):
        return False, "Only HTTP/HTTPS URLs are supported"

    if not parsed.hostname:
        return False, "URL has no hostname"

    if _is_private_ip(parsed.hostname):
        return False, "Private/local URLs are not allowed"

    # Block file:// and other dangerous schemes
    if parsed.scheme == "file":
        return False, "File URLs are not allowed"

    return True, ""


async def fetch_page(url: str) -> tuple[str | None, str | None, str | None]:
    """
    Fetch a web page.
    Returns (html_content, final_url, error).
    """
    is_valid, err = validate_url(url)
    if not is_valid:
        return None, None, err

    try:
        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            follow_redirects=True,
            max_redirects=MAX_REDIRECTS,
        ) as client:
            resp = await client.get(
                url,
                headers={"User-Agent": USER_AGENT},
            )

            if resp.status_code != 200:
                return None, None, f"HTTP {resp.status_code}"

            content_type = resp.headers.get("content-type", "")
            if "text/html" not in content_type and "text/plain" not in content_type:
                return None, None, f"Unsupported content type: {content_type}"

            if len(resp.content) > MAX_CONTENT_LENGTH:
                return None, None, "Page too large (>5MB)"

            return resp.text, str(resp.url), None

    except httpx.TimeoutException:
        return None, None, "Request timed out"
    except httpx.TooManyRedirects:
        return None, None, "Too many redirects"
    except Exception as e:
        return None, None, f"Fetch error: {str(e)[:200]}"


def parse_html(html: str) -> tuple[str, str | None]:
    """
    Parse HTML and extract main content text.
    Returns (text_content, page_title).
    """
    soup = BeautifulSoup(html, "html.parser")

    # Extract title
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else None

    # Remove unwanted elements
    for tag_name in REMOVE_TAGS:
        for el in soup.find_all(tag_name):
            el.decompose()

    # Try to find main content area
    content_el = None
    for selector in CONTENT_TAGS:
        if "[" in selector:
            # Attribute selector like div[role='main']
            tag, attr_str = selector.split("[", 1)
            attr_str = attr_str.rstrip("]")
            key, val = attr_str.split("=", 1)
            val = val.strip("'\"")
            content_el = soup.find(tag, attrs={key: val})
        else:
            content_el = soup.find(selector)
        if content_el:
            break

    # Fall back to body
    if not content_el:
        content_el = soup.find("body") or soup

    # Extract text from relevant tags
    text_parts: list[str] = []
    for el in content_el.find_all(["p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "td", "th", "blockquote", "pre", "code"]):
        txt = el.get_text(separator=" ", strip=True)
        if txt:
            # Preserve heading markers
            if el.name and el.name.startswith("h"):
                level = int(el.name[1])
                txt = "#" * level + " " + txt
            text_parts.append(txt)

    return "\n\n".join(text_parts), title


def sanitize_text(text: str) -> str:
    """
    Sanitize extracted text.
    Removes scripts, hidden content, control characters.
    """
    # Remove any remaining HTML tags
    cleaned = bleach.clean(text, tags=[], strip=True)

    # Normalize unicode
    cleaned = unicodedata.normalize("NFKC", cleaned)

    # Remove control characters (keep newlines and tabs)
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", cleaned)

    # Collapse excessive whitespace
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    return cleaned.strip()


async def scrape_url(url: str) -> tuple[str | None, str | None, str | None]:
    """
    Full scraping pipeline: fetch → parse → sanitize.
    Returns (clean_text, page_title, error).
    """
    html, final_url, err = await fetch_page(url)
    if err:
        return None, None, err

    if not html:
        return None, None, "Empty page content"

    text, title = parse_html(html)
    if not text.strip():
        return None, None, "No extractable text content"

    clean = sanitize_text(text)
    if not clean:
        return None, None, "No content after sanitization"

    # Enforce token limit (rough estimate: 4 chars per token)
    if len(clean) > MAX_TOKENS_PER_LINK * 4:
        clean = clean[: MAX_TOKENS_PER_LINK * 4]

    return clean, title or final_url, None

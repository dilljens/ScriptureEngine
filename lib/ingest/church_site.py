"""Shared fetch + extraction helpers for churchofjesuschrist.org content.

Used by scripts/import_cfm.py and scripts/import_conference.py.

The church site is server-rendered; each article (CFM lesson, conference
talk) has exactly one `<div class="body-block">` holding the body text.
Metadata lives on the TOC/list pages in data-* attributes and link classes.
"""

import hashlib
import re
import time
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

BASE = "https://www.churchofjesuschrist.org"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) ScriptureEngine/1.0"

# Default polite pacing between requests (seconds)
DEFAULT_DELAY = 1.2

_last_request = 0.0


def set_delay(seconds: float):
    """Override the inter-request delay (e.g. --delay 2.0)."""
    global DEFAULT_DELAY
    DEFAULT_DELAY = max(0.0, seconds)


def fetch(url: str, cache_dir: Path | None = None, retries: int = 2) -> str:
    """Fetch a page as HTML text. Optionally cache raw HTML under cache_dir.

    Enforces a minimum delay between requests and retries once on failure.
    """
    global _last_request
    if cache_dir is not None:
        cache_dir = Path(cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        key = hashlib.sha1(url.encode()).hexdigest()[:16]
        cached = cache_dir / f"{key}.html"
        if cached.exists():
            return cached.read_text(encoding="utf-8", errors="ignore")

    wait = DEFAULT_DELAY - (time.monotonic() - _last_request)
    if wait > 0:
        time.sleep(wait)

    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode("utf-8", "ignore")
    except Exception:
        if retries <= 0:
            raise
        time.sleep(2.0)
        return fetch(url, cache_dir=cache_dir, retries=retries - 1)

    _last_request = time.monotonic()
    if cache_dir is not None:
        cached.write_text(html, encoding="utf-8")
    return html


_SKIP_TAGS = {"script", "style", "nav", "figure", "svg", "template"}
_BLOCK_TAGS = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote", "br", "tr"}


class BodyTextExtractor(HTMLParser):
    """Collect the text inside the first <div class="body-block">.

    Preserves paragraph breaks; drops script/style/nav/figure/svg content.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_body = 0      # div.body-block nesting depth
        self.skip = 0         # nested skip-tag depth
        self.out: list[str] = []

    def handle_starttag(self, tag, attrs):
        cls = (dict(attrs).get("class") or "").split()
        if not self.in_body:
            if tag == "div" and "body-block" in cls:
                self.in_body = 1
            return
        if self.skip:
            if tag in _SKIP_TAGS:
                self.skip += 1
            return
        if tag == "div":
            self.in_body += 1
        elif tag in _SKIP_TAGS:
            self.skip += 1
        elif tag in _BLOCK_TAGS:
            self.out.append("\n")

    def handle_endtag(self, tag):
        if not self.in_body:
            return
        if self.skip:
            if tag in _SKIP_TAGS:
                self.skip -= 1
            return
        if tag == "div":
            self.in_body -= 1
        elif tag in _BLOCK_TAGS:
            self.out.append("\n")

    def handle_data(self, data):
        if self.in_body and not self.skip:
            self.out.append(data)

    def text(self) -> str:
        raw = "".join(self.out)
        lines = [re.sub(r"\s+", " ", ln).strip() for ln in raw.split("\n")]
        return "\n".join(ln for ln in lines if ln)


def extract_body(html: str) -> str:
    """Return the article body text (inside div.body-block), tidy."""
    p = BodyTextExtractor()
    p.feed(html)
    return p.text()


def page_title(html: str) -> str:
    """Pull the <title> text, stripped of any ' | ' suffix."""
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S)
    if not m:
        return ""
    title = re.sub(r"\s+", " ", m.group(1)).strip()
    return re.split(r"\s*\|\s*", title)[0].strip()


# ─── TOC parsers ───

def parse_cfm_toc(html: str) -> list[dict]:
    """Parse the CFM manual TOC → weekly lesson entries.

    Entries are <li data-content-type="chapter" data-date-start=".."
    data-date-end=".."> with an <a href=".../<slug>?lang=eng"> and
    <p class="primaryMeta">DATE</p> + <p class="title">BLOCK</p>.
    Returns only pure-numeric week slugs (skips thoughts/appendix pages).
    """
    entries = []
    for m in re.finditer(
        r'<li data-content-type="chapter"\s+data-date-end="([^"]*)"\s+data-date-start="([^"]*)"[^>]*>'
        r'.*?href="/study/manual/[^"]*/([a-z0-9-]+)\?lang=eng"'
        r'.*?<p class="primaryMeta">([^<]*)</p>'
        r'.*?<p class="title[^"]*">([^<]*)</p>',
        html, re.S,
    ):
        date_end, date_start, slug, date_range, block = m.groups()
        if not re.fullmatch(r"\d{1,3}", slug):
            continue  # thoughts / intro / appendix pages
        entries.append({
            "slug": slug.zfill(2),
            "date_range": date_range.strip(),
            "scripture_block": block.strip(),
            "start_date": date_start,
            "end_date": date_end,
        })
    return entries


def parse_conference_toc(html: str) -> dict:
    """Parse a GC session page → {sessions: [...], date_range: (d1, d2) or None}.

    Sessions are <a class="sectionTitle-_Dn99" href=".../SESSION?lang=eng">
    with the session name in a <span>. Talks are
    <a class="item-U_5Ca" href=".../SLUG?lang=eng"> with
    <p><span>TITLE</span></p><p class="subtitle-LKtQp">SPEAKER</p>.
    """
    sessions = []
    current = None
    # Walk sequentially: session headers then talk items
    pattern = re.compile(
        r'<a class="(sectionTitle[^"]*|item-U_5Ca)" href="/study/general-conference/'
        r'(\d{4})/(\d{2})/([a-z0-9-]+)\?lang=eng"[^>]*>'
        r'(?:(?!</a>).)*?<p><span>([^<]*)</span></p>(?:<p class="subtitle-LKtQp">([^<]*)</p>)?',
        re.S,
    )
    for m in pattern.finditer(html):
        cls, year, month, slug, title, speaker = m.groups()
        if "sectionTitle" in cls:
            current = title.strip().replace(" Session", "")
            sessions.append({"session": current, "talks": []})
        elif current is not None:
            sessions[-1]["talks"].append({
                "slug": slug,
                "year": int(year),
                "month": int(month),
                "session": current,
                "title": title.strip(),
                "speaker": (speaker or "").strip(),
            })

    # Conference date(s) — "held on April 5–6, 2025" or "held on April 5, 2025"
    days = None
    m = re.search(r"held on ([A-Za-z]+) (\d{1,2})(?:–|-|—)(\d{1,2})?,?\s*(\d{4})?", html)
    if m:
        month, d1, d2, year_txt = m.groups()
        month_num = {
            "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
            "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
        }.get(month.lower())
        if month_num:
            days = {"month": month_num, "first": int(d1), "second": int(d2 or d1)}
    return {"sessions": sessions, "days": days}

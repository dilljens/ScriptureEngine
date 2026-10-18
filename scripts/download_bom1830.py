"""Download the 1830 first-edition Book of Mormon from Wikisource (proofread text).

Enumerates all subpages under 'Book of Mormon (1830)/' via the MediaWiki API,
fetches wikitext with backoff on 429, and writes:
  data/bom_1830/1830_wikisource_raw.txt   (raw wikitext with section headers)
  data/bom_1830/1830_wikisource_clean.txt (light markup strip for diffing)

Idempotent: skips titles already fetched (progress in data/bom_1830/_progress.json).
Usage: python3 scripts/download_bom1830.py
"""
import json
import os
import re
import time
import urllib.parse
import urllib.request
import urllib.error

BASE = "https://en.wikisource.org/w/api.php"
OUTDIR = "data/bom_1830"
# NOTE: chapter pages are <pages> transclusions from scanned Page: namespace,
# so raw wikitext holds no book text. Fetch rendered HTML (prop=text) instead.
RAW = os.path.join(OUTDIR, "1830_wikisource_html.txt")
CLEAN = os.path.join(OUTDIR, "1830_wikisource_text.txt")
PROG = os.path.join(OUTDIR, "_progress_html.json")
UA = {"User-Agent": "scriptureengine/1.0 (research; contact: local)"}


def api(params, retries=6):
    for attempt in range(retries):
        try:
            q = urllib.parse.urlencode(params)
            req = urllib.request.Request(BASE + "?" + q, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            wait = min(2 ** attempt * 2, 60)
            print(f"HTTP {e.code} {params.get('page', '')[:60]} — sleep {wait}s (try {attempt+1}/{retries})")
            time.sleep(wait)
        except Exception as e:  # network blip
            wait = min(2 ** attempt * 2, 60)
            print(f"ERR {e} — sleep {wait}s (try {attempt+1}/{retries})")
            time.sleep(wait)
    raise RuntimeError(f"API failed after {retries} tries: {params}")


def list_titles():
    titles, cont = [], None
    while True:
        p = {"action": "query", "list": "allpages", "apprefix": "Book of Mormon (1830)/",
             "apnamespace": 0, "aplimit": "max", "format": "json"}
        if cont:
            p.update(cont)
        d = api(p)
        titles += [pg["title"] for pg in d["query"]["allpages"]]
        if "continue" in d:
            cont = d["continue"]
        else:
            break
    return sorted(titles)


def clean_wikitext(wt):
    # rendered HTML from action=parse prop=text: drop style/script, tags, entities
    import html as _html
    wt = re.sub(r"<(style|script)[^>]*>.*?</\1>", " ", wt, flags=re.S | re.I)
    wt = re.sub(r"<[^>]+>", " ", wt)
    wt = _html.unescape(wt)
    wt = re.sub(r"[ \t\xa0]+", " ", wt)
    wt = re.sub(r"\n[ \t]*\n[ \t]*\n+", "\n\n", wt)
    return wt.strip()


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    titles = list_titles()
    print("pages:", len(titles))
    prog = {}
    if os.path.exists(PROG):
        prog = json.load(open(PROG))
    texts = {}
    # reload already-fetched raw sections if present
    if os.path.exists(RAW) and prog.get("done"):
        # re-parse raw file by section headers to resume without refetch
        raw = open(RAW, encoding="utf-8", errors="replace").read()
        parts = re.split(r"\n===== (.*?) =====\n", raw)
        # parts[0] is preamble, then alternating title/body
        for i in range(1, len(parts) - 1, 2):
            texts[parts[i]] = parts[i + 1]
        print("resumed sections:", len(texts))
    for i, t in enumerate(titles):
        if t in texts:
            continue
        d = api({"action": "parse", "page": t, "prop": "text", "format": "json"})
        try:
            wt = d["parse"]["text"]["*"]
        except KeyError:
            print("NO HTML for", t, str(d)[:200])
            wt = ""
        texts[t] = wt
        prog["done"] = sorted(texts.keys())
        json.dump(prog, open(PROG, "w"))
        if i % 10 == 0:
            print(f"{len(texts)}/{len(titles)} {t}")
        time.sleep(1.0)  # be polite to wikisource
    ordered = [t for t in titles if t in texts]
    raw_out = "\n".join(f"\n\n===== {t} =====\n{texts[t]}" for t in ordered)
    open(RAW, "w").write(raw_out)
    clean_out = "\n".join(f"\n\n===== {t} =====\n{clean_wikitext(texts[t])}" for t in ordered)
    open(CLEAN, "w").write(clean_out)
    print("wrote", RAW, len(raw_out), "chars;", CLEAN, len(clean_out), "chars")


if __name__ == "__main__":
    main()

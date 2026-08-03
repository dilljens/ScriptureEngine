#!/usr/bin/env python3
"""Ingest word→image associations for Hebrew vocabulary from open-licensed sources.

Searches Openverse (aggregates Wikimedia Commons + Flickr, CC-licensed) by the
English gloss of each Hebrew vocab lesson, filters to commercial-safe licenses
(cc0/by/by-sa — skips by-nd which forbids cropping), downloads the best image to
data/images/words/, and upserts a LOCAL url + attribution into word_images.

Falls back to the Wikimedia Commons API directly when Openverse returns nothing
usable for a word.

Usage:
    python3 scripts/ingest_word_images.py --dry-run          # Preview, no network/DB writes
    python3 scripts/ingest_word_images.py --limit 25         # First 25 missing words
    python3 scripts/ingest_word_images.py --apply            # Download + write DB
    python3 scripts/ingest_word_images.py --apply --source wikimedia   # Commons only
    python3 scripts/ingest_word_images.py --apply --refresh  # Re-fetch even if image exists

Optional auth (raises Openverse rate limits a lot — free registration at
https://api.openverse.org/): set OPENVERSE_CLIENT_ID / OPENVERSE_CLIENT_SECRET.
"""

import argparse
import json
import os
import re
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE = Path(__file__).parent.parent
SCRIPTURE_DB = BASE / "data" / "processed" / "scripture.db"
MEM_DB = BASE / "data" / "memorize.db"
IMAGE_DIR = BASE / "data" / "images" / "words"
LOCAL_URL_PREFIX = "/images/words/"

# Licenses we accept. by-nd is excluded: we may crop/resize for card display.
GOOD_LICENSES = {"cc0", "by", "by-sa", "pdm", "publicdomain"}
UA = "ScriptureEngine/1.0 (hebrew vocabulary images; contact: local)"

# Openverse anonymous: 20 req/min burst, 200/day sustained. Be gentle.
OPENVERSE_DELAY = 4.0
COMMONS_DELAY = 1.0


def log(msg):
    print(msg, flush=True)


def strip_niqqud(t):
    return re.sub(r"[\u0591-\u05C7]", "", t or "").strip()


def openverse_token():
    cid = os.environ.get("OPENVERSE_CLIENT_ID", "")
    sec = os.environ.get("OPENVERSE_CLIENT_SECRET", "")
    if not (cid and sec):
        return None
    try:
        req = urllib.request.Request(
            "https://api.openverse.org/v1/auth_tokens/token/",
            data=urllib.parse.urlencode({
                "client_id": cid, "client_secret": sec,
                "grant_type": "client_credentials",
            }).encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": UA},
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r).get("access_token")
    except Exception as e:
        log(f"  [openverse auth failed: {e}]")
        return None


def openverse_search(gloss, token=None):
    """Search Openverse; return list of (image_url, attribution, license)."""
    params = {
        "q": gloss,
        "license_type": "commercial",
        "page_size": 10,
        "fields": "url,title,creator,license,attribution,width,height",
    }
    url = "https://api.openverse.org/v1/images/?" + urllib.parse.urlencode(params)
    headers = {"User-Agent": UA}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            data = json.load(r)
    except Exception as e:
        log(f"  [openverse search error: {e}]")
        return []
    results = []
    for item in data.get("results", []):
        lic = (item.get("license") or "").lower().replace("-", "")
        if lic not in GOOD_LICENSES:
            continue
        w, h = item.get("width") or 0, item.get("height") or 0
        # Prefer landscape/portrait-ish, non-tiny images
        if w < 300 or h < 200:
            continue
        results.append({
            "url": item.get("url", ""),
            "attribution": item.get("attribution") or f"Image by {item.get('creator') or 'unknown'} ({item.get('license')})",
            "license": item.get("license", ""),
            "width": w, "height": h,
        })
    return results


def commons_search(gloss):
    """Search Wikimedia Commons; return list of (image_url, attribution, license)."""
    params = {
        "action": "query", "format": "json",
        "generator": "search", "gsrsearch": f"filetype:bitmap {gloss}",
        "gsrnamespace": "6", "gsrlimit": "8",
        "prop": "imageinfo",
        "iiprop": "url|size|extmetadata",
        "iiextmetadatafilter": "LicenseShortName|Artist|Credit|UsageTerms",
    }
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            data = json.load(r)
    except Exception as e:
        log(f"  [commons search error: {e}]")
        return []
    results = []
    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        info = (page.get("imageinfo") or [{}])[0]
        url = info.get("url", "")
        if not url:
            continue
        meta = info.get("extmetadata", {})
        lic = (meta.get("LicenseShortName", {}).get("value", "") or "").lower()
        if "cc" not in lic and "public domain" not in lic and "pd" not in lic.lower():
            continue
        # Attribution: artist + license
        artist = meta.get("Artist", {}).get("value", "")
        artist = re.sub(r"<[^>]+>", "", artist).strip()[:120] or "Wikimedia Commons"
        attribution = f"{page.get('title', '')} — {artist} ({lic})"
        results.append({
            "url": url,
            "attribution": attribution,
            "license": lic,
            "width": info.get("width") or 0,
            "height": info.get("height") or 0,
        })
    return results


def download_image(url, dest, timeout=30):
    """Download url to dest; returns True on success."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            content_type = r.headers.get("Content-Type", "")
            ext = ".jpg"
            if "png" in content_type:
                ext = ".png"
            elif "gif" in content_type:
                ext = ".gif"
            elif "webp" in content_type:
                ext = ".webp"
            if not dest.suffix or dest.suffix.lower() != ext:
                dest = dest.with_suffix(ext)
            data = r.read()
        if len(data) < 500:  # too small to be a real image
            return None
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return dest
    except Exception as e:
        log(f"  [download error {url[:80]}: {e}]")
        return None


def safe_filename(word):
    """Hebrew-safe filename: keep Hebrew letters + digits, drop the rest."""
    return re.sub(r"[^\u0590-\u05FF0-9a-zA-Z]", "", word) or "word"


def already_has_good_image(conn, word_norm):
    """True if a local (non-freebible) image exists for this word."""
    row = conn.execute(
        "SELECT image_url FROM word_images WHERE word_hebrew=? AND source!='freebible' LIMIT 1",
        (word_norm,)).fetchone()
    if not row:
        return False
    local = str(row[0]).startswith(LOCAL_URL_PREFIX) or str(row[0]).startswith("/")
    if local:
        fname = Path(str(row[0])).name
        return (IMAGE_DIR / fname).exists()
    return True


def upsert_image(conn, word, node_id, source, url, attribution, w, h):
    word_norm = strip_niqqud(word)
    if not word_norm:
        return
    conn.execute("""
        INSERT INTO word_images (word_hebrew, node_id, source, image_url, attribution, width, height, prompt)
        VALUES (?,?,?,?,?,?,?,?)
        ON CONFLICT(word_hebrew, source) DO UPDATE SET
            image_url=excluded.image_url, attribution=excluded.attribution,
            width=excluded.width, height=excluded.height
    """, (word_norm, node_id, source, url, attribution, w, h))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Preview only (no network, no DB writes)")
    ap.add_argument("--apply", action="store_true", help="Actually download + write DB")
    ap.add_argument("--limit", type=int, default=0, help="Max words to process (0 = all missing)")
    ap.add_argument("--source", choices=["openverse", "wikimedia"], default="wikimedia",
                    help="Primary image source (wikimedia has no daily cap for bulk runs; "
                         "openverse is better when OPENVERSE_CLIENT_ID/SECRET are set)")
    ap.add_argument("--refresh", action="store_true", help="Re-fetch even if an image exists")
    args = ap.parse_args()

    if not MEM_DB.exists():
        log(f"memorize.db not found: {MEM_DB}")
        sys.exit(1)

    conn = sqlite3.connect(str(MEM_DB))
    conn.row_factory = sqlite3.Row
    # Openverse data lands in the scripture.db word_images table (shared by the
    # /hebrew/image endpoint which reads scripture.db), so upsert there too.
    scr = sqlite3.connect(str(SCRIPTURE_DB)) if SCRIPTURE_DB.exists() else None

    rows = conn.execute("""
        SELECT l.node_id, l.content_json
        FROM hebrew_lessons l JOIN hebrew_nodes n ON n.id=l.node_id
        WHERE n.category IN ('word','noun','verb')
    """).fetchall()

    words = []
    for r in rows:
        try:
            c = json.loads(r["content_json"])
        except (TypeError, json.JSONDecodeError):
            continue
        h = c.get("hebrew", "")
        g = (c.get("gloss") or "").strip()
        if not h or not g:
            continue
        # Take the first gloss before any slash/semicolon — best search term
        term = re.split(r"[/;,]", g)[0].strip()
        words.append({"hebrew": h, "gloss": term, "node_id": r["node_id"]})

    # Dedup by normalized Hebrew
    seen = set()
    unique = []
    for w in words:
        k = strip_niqqud(w["hebrew"])
        if k and k not in seen:
            seen.add(k)
            unique.append(w)

    token = openverse_token() if (args.source == "openverse" and not args.dry_run) else None
    if token:
        log(f"Openverse authenticated (higher rate limits).")
    else:
        log("Openverse anonymous mode — ~4s/word to respect rate limits. "
            "Set OPENVERSE_CLIENT_ID/SECRET for speed.")

    processed = 0
    fetched = 0
    for w in unique:
        if args.limit and processed >= args.limit:
            break
        processed += 1
        word_norm = strip_niqqud(w["hebrew"])

        if scr and not args.refresh and already_has_good_image(scr, word_norm):
            log(f"[{processed}/{len(unique)}] {word_norm} ({w['gloss']}) — already has image")
            continue

        if args.dry_run:
            log(f"[{processed}/{len(unique)}] {word_norm} ({w['gloss']}) → would search '{w['gloss']}'")
            continue

        results = []
        if args.source == "openverse":
            results = openverse_search(w["gloss"], token)
            time.sleep(OPENVERSE_DELAY)
        if not results:
            results = commons_search(w["gloss"])
            time.sleep(COMMONS_DELAY)

        if not results:
            log(f"[{processed}/{len(unique)}] {word_norm} ({w['gloss']}) — no usable image")
            continue

        best = results[0]  # already sorted by relevance from the API
        dest = IMAGE_DIR / f"{safe_filename(word_norm)}.jpg"
        saved = download_image(best["url"], dest)
        if not saved:
            # Try the next candidate
            for alt in results[1:4]:
                saved = download_image(alt["url"], dest)
                if saved:
                    best = alt
                    break
        if not saved:
            log(f"[{processed}/{len(unique)}] {word_norm} ({w['gloss']}) — download failed")
            continue

        local_url = f"{LOCAL_URL_PREFIX}{saved.name}"
        if scr:
            upsert_image(scr, word_norm, w["node_id"], args.source, local_url,
                         best["attribution"], best["width"], best["height"])
            scr.commit()
        log(f"[{processed}/{len(unique)}] {word_norm} ({w['gloss']}) → {local_url} [{best['license']}]")
        fetched += 1

    log(f"\nDone: {fetched} images fetched, {processed} words scanned.")
    if scr:
        scr.close()
    conn.close()


if __name__ == "__main__":
    main()

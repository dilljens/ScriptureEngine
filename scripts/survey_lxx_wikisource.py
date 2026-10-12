#!/usr/bin/env python3
"""Survey en.wikisource Septuagint (Brenton 1879) subpages: length + verse count.
Polite: 3s between requests, honours Retry-After, caches wikitext to disk.
Usage: python3 scripts/survey_lxx_wikisource.py [--refetch]
Writes: /tmp/opencode/lxx_greek_cache/<slug>.wikitext + survey.json
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

UA = "ScriptureEngine-greek-fill/1.0 (local research; contact: local)"
API = "https://en.wikisource.org/w/api.php"
CACHE = "/tmp/opencode/lxx_greek_cache"
os.makedirs(CACHE, exist_ok=True)

PAGES = ["Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy",
         "Joshua", "Judges", "Ruth", "Kings I", "Kings II", "Kings III",
         "Kings IV", "Chronicles I", "Chronicles II", "Ezra", "I Esdras",
         "Nehemiah", "Tobit", "Judith", "Esther (Greek)", "I Maccabees",
         "II Maccabees", "III Maccabees", "IV Maccabees", "Job", "Psalms",
         "Proverbs", "Ecclesiastes", "The Song of Solomon", "Wisdom of Solomon",
         "Sirach", "Esaias", "Jeremias", "Lamentations", "Baruch",
         "Epistle of Jeremy", "Jezekiel", "Daniel (Greek)", "Susanna",
         "Bel and the Dragon", "Osee", "Joel", "Amos", "Obdias", "Jonas",
         "Michæas", "Naum", "Ambacum", "Sophonias", "Aggæus", "Zacharias",
         "Malachias", "Prayer of Manasses"]


def api(params, retries=5):
    q = urllib.parse.urlencode(params)
    for attempt in range(retries):
        try:
            req = urllib.request.Request(API + "?" + q, headers={"User-Agent": UA})
            return json.loads(urllib.request.urlopen(req, timeout=60).read())
        except urllib.error.HTTPError as e:
            wait = int(e.headers.get("Retry-After", "10"))
            print(f"  HTTP {e.code}, waiting {wait}s (attempt {attempt+1})",
                  flush=True)
            time.sleep(wait + 2)
    raise SystemExit("api failed after retries")


import urllib.error  # noqa: E402


def fetch(title, refetch=False):
    slug = title.replace(" ", "_").replace("/", "_")
    path = os.path.join(CACHE, slug + ".wikitext")
    if os.path.exists(path) and not refetch:
        with open(path, encoding="utf-8") as f:
            return f.read()
    d = api({"action": "parse", "page": f"Septuagint (Brenton 1879)/{title}",
             "prop": "wikitext", "format": "json"})
    if "error" in d:
        return f"__ERROR__ {d['error'].get('info', d['error'])}"
    w = d["parse"]["wikitext"]["*"]
    with open(path, "w", encoding="utf-8") as f:
        f.write(w)
    return w


def main():
    refetch = "--refetch" in sys.argv
    out = {}
    for t in PAGES:
        print(f"fetch {t}...", flush=True)
        w = fetch(t, refetch)
        if w.startswith("__ERROR__"):
            out[t] = {"error": w}
            print(f"  {w}")
        else:
            vs = re.findall(r"\{\{verse\|chapter=(\d+)\|verse=([^\}]+)\}\}", w)
            chs = sorted(set(int(c) for c, v in vs)) if vs else []
            out[t] = {"len": len(w), "nverses": len(vs),
                      "nchapters": len(chs), "chapters": chs}
            print(f"  len={len(w)} nverses={len(vs)} nch={len(chs)}")
        time.sleep(3)
    with open(os.path.join(CACHE, "survey.json"), "w") as f:
        json.dump(out, f, indent=1)
    print("wrote survey.json")


if __name__ == "__main__":
    main()

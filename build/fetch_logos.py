#!/usr/bin/env python3
"""Cache organisation favicons as data URIs in build/logos.json.

    python build/fetch_logos.py          # only fetch domains not already cached
    python build/fetch_logos.py --all    # re-fetch everything

Incremental by default, so the weekly refresh only reaches out for
organisations that are new to the dataset. Existing entries are never dropped
because of a failed request - a fetch that fails just leaves the cache as it
was, and the map falls back to a monogram tile for anything uncached.
"""
import argparse
import base64
import csv
import hashlib
import io
import json
import os
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "entries.csv")
LOGOS_PATH = os.path.join(HERE, "logos.json")
UA = {"User-Agent": "Mozilla/5.0 (favicon collector for a static data visualisation)"}


def domain_of(url):
    try:
        host = urllib.parse.urlparse(url).netloc.lower()
        return host[4:] if host.startswith("www.") else host
    except Exception:
        return ""


def grab(domain, size=64):
    url = "https://www.google.com/s2/favicons?sz=%d&domain=%s" % (size, domain)
    try:
        request = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(request, timeout=25) as response:
            body = response.read()
        return body if body and len(body) > 90 else None
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true",
                        help="re-fetch every domain, not just uncached ones")
    args = parser.parse_args()

    with io.open(CSV_PATH, encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    domains = sorted({d for d in (domain_of(r["link"]) for r in rows) if d})

    cache = {}
    if os.path.exists(LOGOS_PATH) and not args.all:
        with io.open(LOGOS_PATH, encoding="utf-8") as handle:
            cache = json.load(handle)

    # drop anything whose organisation has left the dataset
    stale = [d for d in cache if d not in domains]
    for d in stale:
        del cache[d]

    todo = [d for d in domains if d not in cache]
    print("%d domains in dataset, %d already cached, %d to fetch, %d stale removed"
          % (len(domains), len(domains) - len(todo), len(todo), len(stale)))

    if todo:
        # fingerprint the generic globe so it is not mistaken for a real logo
        blanks = set()
        for junk in ("no-such-domain-zzq1x.invalid", "definitely-not-real-4821.test"):
            body = grab(junk)
            if body:
                blanks.add(hashlib.md5(body).hexdigest())

        fetched = {}

        def work(domain):
            body = grab(domain) or grab(domain, 32)
            fetched[domain] = body

        with ThreadPoolExecutor(max_workers=16) as pool:
            list(pool.map(work, todo))

        added = 0
        for domain in todo:
            body = fetched.get(domain)
            if not body or hashlib.md5(body).hexdigest() in blanks:
                continue
            cache[domain] = ("data:image/png;base64,"
                             + base64.b64encode(body).decode("ascii"))
            added += 1
        print("  fetched %d new logo(s); %d had none to find" % (added, len(todo) - added))

    if stale or todo:
        with io.open(LOGOS_PATH, "w", encoding="utf-8", newline="") as handle:
            json.dump(cache, handle, ensure_ascii=True, sort_keys=True)

    covered = sum(1 for r in rows if cache.get(domain_of(r["link"])))
    print("logos.json: %d icons, %d KB; %d of %d organisations covered"
          % (len(cache), sum(len(v) for v in cache.values()) // 1024, covered, len(rows)))


if __name__ == "__main__":
    main()

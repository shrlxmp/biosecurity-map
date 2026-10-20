#!/usr/bin/env python3
"""Rebuild index.html from the biosecurity.world dataset.

    python build/build.py            # rebuild from the committed entries.csv
    python build/build.py --refresh  # re-download entries.csv first

Logos are fetched separately and cached in build/logos.json:

    python build/fetch_logos.py

The page ships as a single self-contained file: organisation data and every
logo are inlined, so it needs no server, no API and no network at run time.
"""
import argparse
import csv
import io
import json
import os
import re
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CSV_URL = "https://biosecurity.world/data/entries.csv"


def split_multi(value):
    """biosecurity.world joins multi-valued fields with ' ; '."""
    return [part.strip() for part in (value or "").split(" ; ") if part.strip()]


def domain_of(url):
    host = urllib.parse.urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


REQUIRED_COLUMNS = {"id", "label", "link", "organization_type", "domains",
                    "activities", "intervention_focuses", "location_hints",
                    "focuses_on_gcbrs", "category_trail", "description"}
MIN_ROWS = 50


def validate(text):
    """Reject anything that isn't recognisably the entries dataset.

    Without this, a moved URL or an interstitial error page would be written
    straight over entries.csv and the next build would publish an empty map.
    """
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows:
        raise SystemExit("refusing to use download: parsed 0 rows")
    missing = REQUIRED_COLUMNS - set(rows[0].keys())
    if missing:
        raise SystemExit("refusing to use download: missing columns %s"
                         % ", ".join(sorted(missing)))
    if len(rows) < MIN_ROWS:
        raise SystemExit("refusing to use download: only %d rows, expected >= %d"
                         % (len(rows), MIN_ROWS))
    return rows


def load_entries(refresh=False):
    path = os.path.join(HERE, "entries.csv")
    if refresh:
        print("downloading", CSV_URL)
        # an explicit User-Agent is required: the default urllib one is
        # rejected with HTTP 403 by the host's bot protection
        request = urllib.request.Request(CSV_URL, headers={
            "User-Agent": "biosecurity-map build script "
                          "(+https://github.com/shrlxmp/biosecurity-map)",
            "Accept": "text/csv,*/*",
        })
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read().decode("utf-8")
        rows = validate(data)          # only overwrite once it looks sane
        io.open(path, "w", encoding="utf-8", newline="").write(data)
        print("  %d rows" % len(rows))
        return rows
    with io.open(path, encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


# biosecurity.world also lists newsletters and podcasts. They are publications,
# not organisations, and most repeat an organisation already on the map.
PUBLICATION = re.compile(r"^(Newsletter|Podcast)\s*-\s*", re.I)


def to_org(row):
    # category_trail looks like "Response > Medical countermeasures"
    trail = [part.strip() for part in (row["category_trail"] or "").split(">")]
    return {
        "id": int(row["id"]),
        "name": row["label"],
        "url": row["link"],
        "dom": domain_of(row["link"]),
        "type": row["organization_type"],
        "domains": split_multi(row["domains"]),
        "act": split_multi(row["activities"]),
        "foci": split_multi(row["intervention_focuses"]),
        "loc": split_multi(row["location_hints"]),
        "gcbr": row["focuses_on_gcbrs"] == "yes",
        "cat": trail[0],
        "sub": trail[1] if len(trail) > 1 else "",
        "desc": row["description"],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true",
                        help="re-download entries.csv from biosecurity.world")
    args = parser.parse_args()

    rows = load_entries(args.refresh)
    orgs = [to_org(row) for row in rows if not PUBLICATION.match(row["label"])]
    orgs.sort(key=lambda org: org["name"].lower())
    skipped = len(rows) - len(orgs)

    logos_path = os.path.join(HERE, "logos.json")
    logos = {}
    if os.path.exists(logos_path):
        with io.open(logos_path, encoding="utf-8") as handle:
            logos = json.load(handle)
    else:
        print("! build/logos.json missing - run build/fetch_logos.py "
              "(the map falls back to monogram tiles without it)")

    used = {org["dom"] for org in orgs}
    logos = {k: v for k, v in logos.items() if k in used}

    with io.open(os.path.join(HERE, "template.html"), encoding="utf-8") as handle:
        page = handle.read()

    # ensure_ascii keeps the output encoding-independent, so organisation
    # names survive regardless of how the page is later served
    page = page.replace("__ORGS__", json.dumps(orgs, ensure_ascii=True,
                                               separators=(",", ":")), 1)
    page = page.replace("__LOGOS__", json.dumps(logos, ensure_ascii=True,
                                                separators=(",", ":")), 1)
    # the count also appears in static copy, so it tracks the weekly refresh
    page = page.replace("__COUNT__", str(len(orgs)))
    if "__ORGS__" in page or "__LOGOS__" in page or "__COUNT__" in page:
        raise SystemExit("template placeholders were not all substituted")

    out = os.path.join(ROOT, "index.html")
    io.open(out, "w", encoding="utf-8", newline="").write(page)

    with_logo = sum(1 for org in orgs if org["dom"] in logos)
    print("wrote %s" % out)
    print("  %d organisations, %d with a logo, %d KB"
          % (len(orgs), with_logo, len(page.encode("utf-8")) // 1024))
    print("  %d newsletters and podcasts left out" % skipped)


if __name__ == "__main__":
    main()

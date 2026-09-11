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


def load_entries(refresh=False):
    path = os.path.join(HERE, "entries.csv")
    if refresh:
        print("downloading", CSV_URL)
        with urllib.request.urlopen(CSV_URL, timeout=60) as response:
            data = response.read().decode("utf-8")
        io.open(path, "w", encoding="utf-8", newline="").write(data)
    with io.open(path, encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


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

    orgs = [to_org(row) for row in load_entries(args.refresh)]
    orgs.sort(key=lambda org: org["name"].lower())

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
    if "__ORGS__" in page or "__LOGOS__" in page:
        raise SystemExit("template placeholders were not both substituted")

    out = os.path.join(ROOT, "index.html")
    io.open(out, "w", encoding="utf-8", newline="").write(page)

    with_logo = sum(1 for org in orgs if org["dom"] in logos)
    print("wrote %s" % out)
    print("  %d organisations, %d with a logo, %d KB"
          % (len(orgs), with_logo, len(page.encode("utf-8")) // 1024))


if __name__ == "__main__":
    main()

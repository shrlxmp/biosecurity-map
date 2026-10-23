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
import unicodedata
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


NAME_STOP = {"the", "inc", "llc", "ltd", "foundation", "corporation", "corp",
             "of", "for", "and", "at", "a"}


def norm_name(name):
    """Fold a name to a comparable key: case, accents, punctuation, filler words."""
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    name = re.sub(r"[^a-z0-9 ]", " ", name.lower().replace("&", " and "))
    return " ".join(w for w in name.split() if w not in NAME_STOP)


def label_forms(label):
    """The ways a map label can be written: the full label, the part before
    " @ ", each with and without its bracketed acronym, and the acronym alone."""
    base = re.split(r"\s+@\s+", label)[0]
    forms = {label, base, re.sub(r"\s*\([^)]*\)", "", label),
             re.sub(r"\s*\([^)]*\)", "", base)}
    forms.update(re.findall(r"\(([^)]+)\)", label))
    return {f for f in forms if norm_name(f)}


def name_keys(orgs):
    """Map every name form to its organisation. A key shared by two
    organisations is dropped as ambiguous."""
    keys = {}
    for org in orgs:
        for form in label_forms(org["name"]):
            keys.setdefault(norm_name(form), set()).add(org["id"])
    return {k: next(iter(v)) for k, v in keys.items() if len(v) == 1}


def norm_link(url):
    parts = urllib.parse.urlparse(url.strip().lower())
    host = parts.netloc[4:] if parts.netloc.startswith("www.") else parts.netloc
    return host + parts.path.rstrip("/")


def load_extras(upstream):
    """Organisations this map adds while biosecurity.world reviews them.

    build/extra_entries.csv uses biosecurity.world's own columns. A row is
    retired, with a notice, as soon as the upstream dataset lists the same
    organisation (same link, or a matching name), so the two never both show."""
    path = os.path.join(HERE, "extra_entries.csv")
    if not os.path.exists(path):
        return []
    with io.open(path, encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if rows:
        missing = REQUIRED_COLUMNS - set(rows[0].keys())
        if missing:
            raise SystemExit("extra_entries.csv is missing columns %s"
                             % ", ".join(sorted(missing)))
    keys = name_keys(upstream)
    links = {norm_link(org["url"]) for org in upstream}
    ids = {org["id"] for org in upstream}
    extras = []
    for row in rows:
        org = to_org(row)
        if org["id"] in ids:
            raise SystemExit("extra_entries.csv id %d clashes with biosecurity.world" % org["id"])
        hit = (norm_link(org["url"]) in links
               or any(norm_name(f) in keys for f in label_forms(org["name"])))
        if hit:
            print("  extra %r is now in biosecurity.world's data: left out, "
                  "delete its row from build/extra_entries.csv" % org["name"])
            continue
        org["extra"] = True
        extras.append(org)
    return extras


def load_funding(orgs):
    """Coefficient Giving's biosecurity grants, each linked to an organisation
    on the map where the recipient is one. Returns None if the data is absent."""
    path = os.path.join(HERE, "funding_cg.json")
    if not os.path.exists(path):
        print("! build/funding_cg.json missing - run build/fetch_funding.py "
              "(the funding view is left empty without it)")
        return None
    with io.open(path, encoding="utf-8") as handle:
        doc = json.load(handle)
    with io.open(os.path.join(HERE, "funding_aliases.json"), encoding="utf-8") as handle:
        aliases = json.load(handle)

    by_label = {org["name"]: org["id"] for org in orgs}
    for target in ([r["org"] for r in aliases["by_title"]]
                   + list(aliases["by_recipient"].values())):
        if target not in by_label:
            print("! funding_aliases.json names %r, which is not on the map" % target)
    keys = name_keys(orgs)

    def org_for(grant):
        for rule in aliases["by_title"]:
            if (grant["org"] == rule["recipient"]
                    and re.search(rule["title"], grant["title"])):
                return by_label.get(rule["org"])
        if grant["org"] in aliases["by_recipient"]:
            return by_label.get(aliases["by_recipient"][grant["org"]])
        return keys.get(norm_name(grant["org"]))

    grants, unmatched = [], {}
    for grant in doc["grants"]:
        org_id = org_for(grant)
        amount = grant["amount"] or 0
        if org_id is None:
            unmatched[grant["org"]] = unmatched.get(grant["org"], 0) + amount
        # compact rows: year, amount, organisation id (or null), recipient, title
        grants.append([grant["year"], amount, org_id, grant["org"], grant["title"]])

    total = sum(g[1] for g in grants)
    on_map = sum(g[1] for g in grants if g[2] is not None)
    print("  funding: %d grants, $%.1fM, of which $%.1fM (%d%%) to %d organisations on the map"
          % (len(grants), total / 1e6, on_map / 1e6, round(100 * on_map / (total or 1)),
             len({g[2] for g in grants if g[2] is not None})))
    for name, amount in sorted(unmatched.items(), key=lambda kv: -kv[1])[:8]:
        print("    not on the map: $%.1fM %s" % (amount / 1e6, name or "(unnamed)"))
    return {"exported_at": doc.get("exported_at"), "grants": grants}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true",
                        help="re-download entries.csv from biosecurity.world")
    args = parser.parse_args()

    rows = load_entries(args.refresh)
    orgs = [to_org(row) for row in rows if not PUBLICATION.match(row["label"])]
    skipped = len(rows) - len(orgs)
    extras = load_extras(orgs)
    orgs += extras
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
    page = page.replace("__FUNDING__", json.dumps(load_funding(orgs), ensure_ascii=True,
                                                  separators=(",", ":")), 1)
    # the count also appears in static copy, so it tracks the weekly refresh
    page = page.replace("__COUNT__", str(len(orgs)))
    # credit line under the title, saying how many organisations this map added
    source = ('Data from <a href="https://biosecurity.world/" target="_blank" '
              'rel="noopener">biosecurity.world</a>')
    if extras:
        source += (", plus %d organisation%s added here that it does not list yet"
                   % (len(extras), "" if len(extras) == 1 else "s"))
    page = page.replace("__SOURCE__", source + ".")
    if any(p in page for p in ("__ORGS__", "__LOGOS__", "__FUNDING__", "__COUNT__",
                               "__SOURCE__")):
        raise SystemExit("template placeholders were not all substituted")

    out = os.path.join(ROOT, "index.html")
    io.open(out, "w", encoding="utf-8", newline="").write(page)

    with_logo = sum(1 for org in orgs if org["dom"] in logos)
    print("wrote %s" % out)
    print("  %d organisations, %d with a logo, %d KB"
          % (len(orgs), with_logo, len(page.encode("utf-8")) // 1024))
    print("  %d newsletters and podcasts left out, %d organisations added from "
          "build/extra_entries.csv" % (skipped, len(extras)))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Refresh build/funding/*.json: biosecurity grants from philanthropic funders.

    python build/fetch_funding.py              # every funder
    python build/fetch_funding.py gates sff    # just these

One file per funder, each saying in plain words which of that funder's grants
count as biosecurity and which recipients they are counted for. Where a funder
labels its own biosecurity grants we use its label; where it doesn't, the rule
is ours and the file says so.

Each funder is fetched and validated on its own. If one fails, its existing
file is kept and the others still refresh; the script then exits non-zero so
the weekly workflow shows a warning. Output is deterministic, so a run that
finds nothing new leaves the files byte-identical.
"""
import csv
import html
import io
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "funding")
UA = {"User-Agent": "biosecurity-map build script "
                    "(+https://github.com/shrlxmp/biosecurity-map)"}
TRACE_RAW = "https://raw.githubusercontent.com/manifund/trace/main/data/"


def get(url, timeout=90):
    request = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8-sig", errors="replace")


def text(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def require(condition, message):
    if not condition:
        raise ValueError(message)


# ---------------------------------------------------------------- Coefficient Giving

CG_AREAS = ["Biosecurity & Pandemic Preparedness",
            "Science Supporting Biosecurity and Pandemic Preparedness"]


def coefficient_giving():
    """Full export of the grants database kept in Trace's open repository."""
    doc = json.loads(get(TRACE_RAW + "coefficient-grants.json"))
    grants = doc.get("grants") or []
    require(len(grants) >= 1000, "expected >= 1000 grants, got %d" % len(grants))
    require({"id", "org", "title", "year", "amount", "areas"} <= set(grants[0]),
            "grant records are missing fields")
    keep = [g for g in grants if set(CG_AREAS) & set(g.get("areas") or [])]
    require(keep, "no grants in the biosecurity areas")
    return {
        "funder": "Coefficient Giving",
        "funder_org": "Coefficient Giving, Biosecurity & Pandemic Preparedness team",
        "rule": "Grants in Coefficient Giving's own two biosecurity focus areas.",
        "scope": "all",
        "source_url": "https://github.com/manifund/trace/blob/main/data/coefficient-grants.json",
        "exported_at": doc.get("exported_at"),
        "grants": [{"id": g["id"], "year": g["year"], "recipient": (g.get("org") or "").strip(),
                    "title": g.get("title") or "", "amount": g.get("amount")} for g in keep],
    }


# ---------------------------------------------------------------- Gates Foundation

GATES_CSV = "https://www.gatesfoundation.org/-/media/files/bmgf-grants.csv"
# Gates has no biosecurity label: its "Pneumonia & Pandemic Preparedness" topic
# is mostly childhood pneumonia, RSV and pneumococcal vaccines. So a grant
# counts when its stated purpose names pandemic or epidemic threats...
GATES_BIO = re.compile(
    r"pandemic|biosecurity|biosafety|biodefen|outbreak|"
    r"epidemic (?:preparedness|response|intelligence|threat)|covid|sars-cov|coronavirus|"
    r"\bmers\b|ebola|marburg|lassa|nipah|henipa|mpox|monkeypox|\bh5n1\b|avian influenza|"
    r"universal (?:flu|influenza)|emerging (?:infectious|pathogen|disease)|"
    r"priority pathogen|health security|100 days mission|disease x", re.I)
# ...unless it is about a routine disease and only says "pandemic" in passing
# (e.g. "the global HIV/AIDS pandemic", polio outbreak response)
GATES_ROUTINE = re.compile(
    r"polio|measles|cholera|malaria|tuberculosis|\bHIV\b|\bAIDS\b|typhoid|rotavirus|"
    r"pneumococc|meningitis|respiratory syncytial|\bRSV\b", re.I)
GATES_STRONG = re.compile(
    r"pandemic preparedness|pandemics|pandemic influenza|biosecurity|biosafety|"
    r"health security|covid|sars-cov|coronavirus|epidemic preparedness|100 days mission|"
    r"disease x", re.I)
# and not from divisions that never fund pandemic work (this drops e.g. a US
# Program grant on COVID's effect on schools); Gavi's COVID vaccine grant sits
# in Global Development, so that division stays
GATES_DIVISIONS = re.compile(r"Global Health|Global Development|Global Policy|Executive|"
                             r"Africa & India")


def gates():
    raw = get(GATES_CSV, timeout=180)
    first, body = raw.split("\n", 1)
    csv.field_size_limit(10 ** 8)
    rows = [r for r in csv.DictReader(io.StringIO(body)) if r.get("GRANT ID")]
    require(len(rows) >= 10000, "expected >= 10000 grants, got %d" % len(rows))
    require({"GRANTEE", "PURPOSE", "DIVISION", "DATE COMMITTED", "AMOUNT COMMITTED"}
            <= set(rows[0]), "CSV is missing columns")
    keep = []
    for r in rows:
        purpose = r.get("PURPOSE") or ""
        if not (GATES_BIO.search(purpose) and GATES_DIVISIONS.search(r.get("DIVISION") or "")):
            continue
        if GATES_ROUTINE.search(purpose) and not GATES_STRONG.search(purpose):
            continue
        amount = (r.get("AMOUNT COMMITTED") or "").replace(",", "").replace("$", "").strip()
        keep.append({"id": r["GRANT ID"], "year": int((r.get("DATE COMMITTED") or "0")[:4]),
                     "recipient": (r.get("GRANTEE") or "").strip(),
                     "title": purpose.strip()[:300],
                     "amount": round(float(amount)) if amount else None})
    require(len(keep) >= 100, "only %d grants passed the rule" % len(keep))
    return {
        "funder": "Gates Foundation",
        "funder_org": "Gates Foundation",
        "rule": ("Gates does not label biosecurity grants, so this is our rule: grants from "
                 "its global health, development and policy divisions whose stated purpose names "
                 "pandemic or epidemic threats (pandemics, outbreaks, biosecurity, COVID-19, Ebola, "
                 "henipaviruses and similar), leaving out routine diseases such as polio, "
                 "HIV or malaria unless the purpose is about pandemic preparedness. Counted "
                 "only for organisations on the map, because the rule is too loose to trust "
                 "for everyone else."),
        "scope": "on_map_only",
        "source_url": "https://www.gatesfoundation.org/about/committed-grants",
        "exported_at": first.strip().strip('"').replace("Updated ", ""),
        "grants": keep,
    }


# ---------------------------------------------------------------- Sentinel Bio

SENTINEL = "https://sentinelbio.org/research-and-projects/"
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august",
          "september", "october", "november", "december"]


def sentinel_bio():
    page = get(SENTINEL)
    cards = re.findall(r'(?is)<a[^>]+class="[^"]*\bgrant\b[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
                       page)
    cards += re.findall(r'(?is)<a[^>]+href="([^"]+)"[^>]+class="[^"]*\bgrant\b[^"]*"[^>]*>(.*?)</a>',
                        page)
    keep, seen = [], set()
    for link, inner in cards:
        slug = re.search(r"/grant/([^/]+)/?$", link)
        if not slug or slug.group(1) in seen:
            continue
        seen.add(slug.group(1))
        name = re.search(r'(?is)class="[^"]*\bname\b[^"]*"[^>]*>(.*?)</', inner)
        details = re.search(r'(?is)class="[^"]*\bdetails\b[^"]*"[^>]*>(.*)', inner)
        cells = [text(c) for c in re.findall(r"(?is)<div[^>]*>(.*?)</div>",
                                             details.group(1))] if details else []
        month, programme, amount = (cells + ["", "", ""])[:3]
        when = re.match(r"([a-z]+)\s+(\d{4})$", month.strip().lower())
        if not (name and when and when.group(1) in MONTHS):
            continue
        digits = re.search(r"\$\s*([\d,]+)", amount)
        title = programme or "Grant"
        if "*" in amount:
            # starred: an external partner's money, given on Sentinel's recommendation
            title += " (funded by an external partner on Sentinel Bio's recommendation)"
        keep.append({"id": slug.group(1), "year": int(when.group(2)),
                     "recipient": text(name.group(1)), "title": title,
                     "amount": int(digits.group(1).replace(",", "")) if digits else None})
    require(len(keep) >= 40, "only %d grants parsed; has the page changed?" % len(keep))
    return {
        "funder": "Sentinel Bio",
        "funder_org": "Sentinel Bio",
        "rule": "All of Sentinel Bio's grants. It funds biosecurity only.",
        "scope": "all",
        "source_url": SENTINEL,
        "exported_at": None,
        "grants": sorted(keep, key=lambda g: (-g["year"], g["id"])),
    }


# ---------------------------------------------------------------- Survival and Flourishing Fund

SFF = "https://survivalandflourishing.fund/recommendations"
# SFF does not label grants, and most organisations it funds on the map work on
# several risks at once (AI, food resilience, catastrophic risk in general). So
# only these, whose main work is biosecurity, are counted; checked by hand.
SFF_ORGS = ["SecureBio", "SecureDNA", "Amodo Design", "Blueprint Biosecurity"]


def sff():
    page = get(SFF)
    keep = []
    for tr in re.findall(r"(?is)<tr[^>]*>(.*?)</tr>", page):
        cells = [text(c) for c in re.findall(r"(?is)<td[^>]*>(.*?)</td>", tr)]
        if len(cells) != 6:
            continue
        rnd, source, org, amount, _charity, purpose = cells
        year = re.search(r"(\d{4})", rnd)
        dollars = [int(m.replace(",", "")) for m in re.findall(r"\$([\d,]+)", amount)]
        if not (org and year and dollars):
            continue
        recipient = re.sub(r"\s*\[[^\]]*\]\s*$", "", org).strip().rstrip("*").strip()
        keep.append({"id": "%s|%s|%s" % (rnd, recipient, sum(dollars)), "year": int(year.group(1)),
                     "recipient": recipient, "title": "%s (%s, via %s)" % (purpose or "Grant", rnd, source),
                     "amount": sum(dollars)})
    require(len(keep) >= 300, "only %d rows parsed; has the page changed?" % len(keep))
    keep.sort(key=lambda g: (-g["year"], g["id"]))
    return {
        "funder": "Survival and Flourishing Fund",
        "funder_org": "Survival & Flourishing Fund",
        "rule": ("SFF does not label biosecurity grants, and most organisations it funds work "
                 "on several risks at once. So only its grants to organisations whose main "
                 "work is biosecurity are counted: " + ", ".join(SFF_ORGS) + "."),
        "scope": "listed_only",
        "only_orgs": SFF_ORGS,
        "source_url": SFF,
        "exported_at": None,
        "grants": keep,
    }


# ---------------------------------------------------------------- funders via Trace

def from_trace(name, funder, funder_org, rule, keep_if):
    grants = json.loads(get(TRACE_RAW + "curated/%s.json" % name)).get("grants") or []
    require(len(grants) >= 10, "expected >= 10 grants, got %d" % len(grants))
    keep = []
    for i, g in enumerate(grants):
        year = re.match(r"(\d{4})", g.get("date") or "")
        if not (year and keep_if(g)) or (g.get("currency") or "USD") != "USD":
            continue
        keep.append({"id": "%s-%d" % (name, i), "year": int(year.group(1)),
                     "recipient": (g.get("recipient") or "").strip(),
                     "title": (g.get("description") or g.get("program") or "")[:300],
                     "amount": g.get("amount")})
    require(keep, "no biosecurity grants found")
    return {"funder": funder, "funder_org": funder_org, "rule": rule, "scope": "all",
            "source_url": "https://github.com/manifund/trace/blob/main/data/curated/%s.json" % name,
            "exported_at": None, "grants": keep}


def openai_foundation():
    return from_trace("openai-foundation", "OpenAI Foundation", None,
                      "Grants Trace tags as biosecurity.",
                      lambda g: "biosecurity" in (g.get("causes") or []))


LONGVIEW_BIO = re.compile(r"biosecur|pandemic|pathogen|biolog|far-uvc|dna synthesis|biorisk", re.I)


def longview():
    return from_trace(
        "longview", "Longview Philanthropy", "Longview Philanthropy",
        "Grants in Longview's biosecurity programme, or whose description names biosecurity "
        "work (pathogens, pandemics, biological risk, far-UVC, DNA synthesis). Includes grants "
        "it advised donors to make.",
        lambda g: "biosecurity" in (g.get("program") or "").lower()
        or LONGVIEW_BIO.search((g.get("recipient") or "") + " " + (g.get("description") or "")))


SOURCES = {"coefficient_giving": coefficient_giving, "gates": gates,
           "sentinel_bio": sentinel_bio, "sff": sff,
           "openai_foundation": openai_foundation, "longview": longview}


def main():
    wanted = sys.argv[1:] or list(SOURCES)
    os.makedirs(OUT_DIR, exist_ok=True)
    failed = []
    for key in wanted:
        try:
            doc = SOURCES[key]()
        except Exception as error:  # keep the last good file and carry on
            print("! %s: %s - keeping the existing file" % (key, error))
            failed.append(key)
            continue
        doc = dict({"_comment": "Generated by build/fetch_funding.py; do not edit by hand.",
                    "key": key}, **doc)
        path = os.path.join(OUT_DIR, key + ".json")
        out = json.dumps(doc, ensure_ascii=True, indent=1, sort_keys=True) + "\n"
        old = io.open(path, encoding="utf-8").read() if os.path.exists(path) else None
        total = sum(g["amount"] or 0 for g in doc["grants"])
        if out == old:
            print("%-18s no change: %d grants, $%.1fM" % (key, len(doc["grants"]), total / 1e6))
            continue
        io.open(path, "w", encoding="utf-8", newline="").write(out)
        print("%-18s wrote %d grants, $%.1fM" % (key, len(doc["grants"]), total / 1e6))
    if failed:
        raise SystemExit("failed: " + ", ".join(failed))


if __name__ == "__main__":
    main()

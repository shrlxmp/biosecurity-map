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
import datetime
import html
import io
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

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
    r"pneumococc|streptococc|meningitis|respiratory syncytial|\bRSV\b|gonorrh|syphilis|"
    r"chlamydia", re.I)
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


# ---------------------------------------------------------------- Wellcome

REGISTRY = "https://registry.threesixtygiving.org/data.json"
# annual average US dollars per pound, for converting Wellcome's grants; the
# same kind of approximation Trace uses, good enough for totals
USD_PER_GBP = {2000: 1.516, 2001: 1.440, 2002: 1.501, 2003: 1.634, 2004: 1.832,
               2005: 1.820, 2006: 1.843, 2007: 2.002, 2008: 1.853, 2009: 1.566,
               2010: 1.546, 2011: 1.604, 2012: 1.585, 2013: 1.564, 2014: 1.648,
               2015: 1.528, 2016: 1.355, 2017: 1.289, 2018: 1.335, 2019: 1.277,
               2020: 1.284, 2021: 1.375, 2022: 1.237, 2023: 1.244, 2024: 1.278,
               2025: 1.298, 2026: 1.310}
# Wellcome descriptions are long and mention pandemics in passing, so a
# description alone counts only when it is plainly about preparedness
WELLCOME_DESC = re.compile(r"pandemic preparedness|epidemic preparedness|biosecurity|biosafety|"
                           r"pandemic threat|100 days mission|disease x", re.I)


def xlsx_rows(data):
    """Rows of the first sheet of an .xlsx file, using only the standard library."""
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    book = zipfile.ZipFile(io.BytesIO(data))
    shared = []
    if "xl/sharedStrings.xml" in book.namelist():
        for item in ET.fromstring(book.read("xl/sharedStrings.xml")).iter(ns + "si"):
            shared.append("".join(t.text or "" for t in item.iter(ns + "t")))
    sheet = sorted(n for n in book.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml$", n))[0]
    rows = []
    for _, el in ET.iterparse(book.open(sheet)):
        if el.tag != ns + "row":
            continue
        row = {}
        for cell in el.iter(ns + "c"):
            col = 0
            for ch in re.match(r"[A-Z]+", cell.get("r")).group():
                col = col * 26 + ord(ch) - 64
            value, kind = cell.find(ns + "v"), cell.get("t")
            if kind == "s" and value is not None:
                row[col - 1] = shared[int(value.text)]
            elif kind == "inlineStr":
                row[col - 1] = "".join(t.text or "" for t in cell.iter(ns + "t"))
            else:
                row[col - 1] = value.text if value is not None else ""
        rows.append([row.get(i, "") for i in range(max(row) + 1)] if row else [])
        el.clear()
    return rows


def wellcome():
    # the file name changes with every release, so find it in the 360Giving registry
    registry = json.loads(get(REGISTRY, timeout=120))
    datasets = [d for d in registry
                if (d.get("publisher") or {}).get("prefix") == "360G-wellcome"
                and (d.get("title") or "").startswith("Grants awarded")]
    require(datasets, "Wellcome's grants are not in the 360Giving registry")
    dataset = max(datasets, key=lambda d: d.get("modified") or "")
    url = dataset["distribution"][0]["downloadURL"]
    request = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(request, timeout=300) as response:
        rows = xlsx_rows(response.read())
    head, body = rows[0], [dict(zip(rows[0], r)) for r in rows[1:] if r]
    require(len(body) >= 10000, "expected >= 10000 grants, got %d" % len(body))
    require({"Recipient Org:Name", "Title", "Description", "Amount Awarded", "Currency",
             "Award Date", "Identifier"} <= set(head), "spreadsheet is missing columns")
    keep = []
    for r in body:
        title, desc = (r.get("Title") or "").strip(), r.get("Description") or ""
        by_title = (GATES_BIO.search(title)
                    and not (GATES_ROUTINE.search(title) and not GATES_STRONG.search(title)))
        if not (by_title or (WELLCOME_DESC.search(desc) and not GATES_ROUTINE.search(title))):
            continue
        try:  # award dates are Excel day numbers
            year = (datetime.date(1899, 12, 30)
                    + datetime.timedelta(days=float(r["Award Date"]))).year
        except (TypeError, ValueError):
            year = int((r.get("Financial Year") or "0")[:4])
        amount = float(r.get("Amount Awarded") or 0)
        if (r.get("Currency") or "GBP") == "GBP":
            amount *= USD_PER_GBP.get(year, USD_PER_GBP[2026])
        elif r.get("Currency") != "USD":
            continue
        keep.append({"id": r["Identifier"], "year": year,
                     "recipient": (r.get("Recipient Org:Name") or "").strip(),
                     "title": title[:300], "amount": round(amount)})
    require(len(keep) >= 50, "only %d grants passed the rule" % len(keep))
    keep.sort(key=lambda g: (-g["year"], g["id"]))
    return {
        "funder": "Wellcome",
        "funder_org": "Wellcome Trust",
        "rule": ("Wellcome does not label biosecurity grants, so this is our rule: grants whose "
                 "title names pandemic or epidemic threats (pandemics, outbreaks, COVID-19, Ebola "
                 "and similar), or whose description is plainly about pandemic preparedness or "
                 "biosecurity, leaving out routine diseases. Pounds are converted to dollars at "
                 "each year's average rate. Counted only for organisations on the map, because "
                 "the rule is too loose to trust for everyone else."),
        "scope": "on_map_only",
        "source_url": dataset["distribution"][0].get("accessURL") or url,
        "exported_at": (dataset.get("modified") or "")[:10] or None,
        "grants": keep,
    }


# ---------------------------------------------------------------- US federal government

USASPENDING = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
# departments that fund biodefense and pandemic work; Energy (national-lab
# operating contracts) and Veterans Affairs (routine drug purchases) are left out
US_AGENCIES = ["Department of Health and Human Services", "Department of Defense",
               "Department of Homeland Security", "Agency for International Development",
               "Department of State"]
# preparedness is the whole remit of HHS's preparedness office (BARDA's parent),
# so its awards count whatever their description says ("Biomedical (advanced)")
ASPR = "Office of Assistant Secretary for Preparedness and Response"
# ...except its chemical, radiological and nuclear work
NOT_BIO = re.compile(r"sulfur mustard|mustard gas|nerve agent|organophosph|chlorine|cyanide|"
                     r"radiolog|radiation|nuclear|\barcs?\b|burn injur|thermal burn|co-60|"
                     r"cobalt|cesium", re.I)
BIO_NAMED = re.compile(r"biolog|pathogen|virus|viral|vaccin|bacteri|anthrax|smallpox|covid|"
                       r"sars|ebola|influenza|pandemic|toxin|plague|filovir", re.I)
US_TYPES = {"contract": ["A", "B", "C", "D"], "grant": ["02", "03", "04", "05"]}
US_BIO = re.compile(
    GATES_BIO.pattern + r"|sars-cov-2|mrna-1273|bnt162|biodefen|"
    # not the combined "chemical, biological, radiological and nuclear" phrase on
    # its own: those programmes are mostly chemical and radiological testing
    r"biological (?:threat|weapon|agent|defense|warfare)|select agent|"
    r"anthrax|smallpox|botulinum|\bplague\b|tularemia|medical countermeasure|"
    r"\bbarda\b|project nextgen|warp speed|pandemic influenza|\bh7n9\b|biosurveillance|"
    r"biothreat|filovir|equine encephalitis|biowatch|\bnbacc\b|"
    # named pandemic and biodefense products, whose award descriptions often give
    # only the product name (Paxlovid is "oral protease inhibitor PF-07321332")
    r"paxlovid|nirmatrelvir|pf-07321332|molnupiravir|mk-4482|remdesivir|bebtelovimab|"
    r"sotrovimab|bamlanivimab|casirivimab|regen-cov|evusheld|tixagevimab|ervebo|jynneos|"
    r"acam2000|tpoxx|tecovirimat|brincidofovir|biothrax|cyfendus|anthrasil|raxibacumab|"
    r"obiltoxaximab", re.I)
# sent to the API so it only returns likely awards; the local rule above decides
US_KEYWORDS = ["pandemic", "covid", "covid-19", "sars-cov-2", "coronavirus", "biodefense",
               "anthrax", "smallpox", "ebola", "countermeasure", "biological", "barda",
               "mrna-1273", "h5n1", "avian", "mpox", "monkeypox", "marburg", "nipah",
               "filovirus", "plague", "botulinum", "outbreak", "biothreat", "nextgen",
               "paxlovid", "molnupiravir", "ervebo", "jynneos", "pf-07321332"]


def us_post(body):
    request = urllib.request.Request(USASPENDING, data=json.dumps(body).encode(),
                                     headers=dict(UA, **{"content-type": "application/json"}))
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read())


def us_awards(name, codes, scope):
    """Every award for one recipient search, page by page, largest first."""
    for page in range(1, 41):
        data = us_post({
            "filters": dict({"recipient_search_text": [name], "award_type_codes": codes,
                             "time_period": [{"start_date": "2007-10-01",
                                              "end_date": "2026-09-30"}]}, **scope),
            "fields": ["Award ID", "Recipient Name", "Award Amount", "Awarding Agency",
                       "Awarding Sub Agency", "Description", "Start Date"],
            "limit": 100, "page": page, "sort": "Award Amount", "order": "desc"})
        yield from data.get("results") or []
        if not (data.get("page_metadata") or {}).get("hasNext"):
            return
    print("  note: stopped after 40 pages for %s; only its smallest awards are missed" % name)


def us_federal():
    config = json.load(io.open(os.path.join(HERE, "government_recipients.json"), encoding="utf-8"))
    every_agency = {"keywords": US_KEYWORDS,
                    "agencies": [{"type": "awarding", "tier": "toptier", "name": a}
                                 for a in US_AGENCIES]}
    aspr_only = {"agencies": [{"type": "awarding", "tier": "subtier", "name": ASPR}]}
    keep, seen, checked = [], set(), 0
    for label, spec in sorted(config["recipients"].items()):
        names = spec["names"] if isinstance(spec, dict) else spec
        wanted = {re.sub(r"\s+", " ", n).upper() for n in names}
        must = re.compile(spec["description"], re.I) if isinstance(spec, dict) else None
        for name in names:
            for kind, codes in US_TYPES.items():
                for scope in (every_agency, aspr_only):
                    for r in us_awards(name, codes, scope):
                        checked += 1
                        key = r.get("generated_internal_id") or r.get("Award ID")
                        who = re.sub(r"\s+", " ", r.get("Recipient Name") or "").upper()
                        desc = r.get("Description") or ""
                        amount = r.get("Award Amount") or 0
                        if key in seen or who not in wanted or amount <= 0:
                            continue
                        if must and not must.search(desc):
                            continue
                        if NOT_BIO.search(desc) and not BIO_NAMED.search(desc):
                            continue  # chemical, radiological or nuclear work
                        from_aspr = (r.get("Awarding Sub Agency") or "") == ASPR
                        if not (from_aspr or US_BIO.search(desc)):
                            continue
                        if GATES_ROUTINE.search(desc) and not GATES_STRONG.search(desc):
                            continue
                        year = re.match(r"(\d{4})", r.get("Start Date") or "")
                        if not year:
                            continue
                        seen.add(key)
                        keep.append({"id": key, "year": int(year.group(1)), "recipient": label,
                                     "title": "%s (%s, %s)" % (
                                         re.sub(r"\s+", " ", desc).strip().capitalize()[:240],
                                         r.get("Awarding Sub Agency") or r.get("Awarding Agency"),
                                         kind),
                                     "amount": round(amount)})
    require(checked >= 100, "only %d awards came back; is the API down?" % checked)
    require(keep, "no awards passed the rule")
    keep.sort(key=lambda g: (-g["year"], str(g["id"])))
    return {
        "funder": "US federal government",
        "funder_org": None,
        "kind": "government",
        "rule": ("Contracts, grants and cooperative agreements from the departments of Health and "
                 "Human Services (including NIH and CDC), Defense and Homeland Security, USAID and "
                 "State, whose description names pandemic or biodefense work (pandemics, COVID-19, "
                 "biological threats, anthrax, smallpox, medical countermeasures, or named products "
                 "such as Paxlovid), leaving out routine diseases. Every award from HHS's "
                 "preparedness office (ASPR, which runs BARDA) counts, except its chemical, "
                 "radiological and nuclear work. Only for a hand-checked list "
                 "of organisations on the map: university-based centres are left out because their "
                 "awards go to the university. Awards made through contracting consortia (much of "
                 "Operation Warp Speed, including Novavax's main COVID-19 award) are listed under "
                 "the consortium and so are missing. Amounts are total obligations, including "
                 "purchases such as vaccine doses."),
        "scope": "on_map_only",
        "source_url": "https://www.usaspending.gov/",
        "exported_at": None,
        "grants": keep,
    }


def government_config():
    return json.load(io.open(os.path.join(HERE, "government_recipients.json"), encoding="utf-8"))


# a looser rule for grants already tied to a biosecurity centre through the
# researcher who leads it: seasonal flu tracking and outbreak modelling count
CENTRE_BIO = re.compile(US_BIO.pattern + r"|influenza|phylodynam|genomic (?:surveillance|epidemiology)|"
                        r"pathogen surveillance|emerging infect|transmission|epidemic|"
                        r"virus evolution|viral evolution|biosecur|"
                        r"communicable disease dynamics", re.I)


def routine(text):
    return GATES_ROUTINE.search(text) and not GATES_STRONG.search(text)


# ---------------------------------------------------------------- NIH, for university centres

NIH = "https://api.reporter.nih.gov/v2/projects/search"


def nih_centres():
    config = government_config()["nih_pis"]
    keep, seen = [], set()
    for label, spec in sorted(config.items()):
        org = re.compile(spec["org"], re.I)
        for first, last in spec["pis"]:
            offset = 0
            while True:
                request = urllib.request.Request(NIH, data=json.dumps({
                    "criteria": {"pi_names": [{"first_name": first, "last_name": last}]},
                    "include_fields": ["ApplId", "ProjectNum", "FiscalYear", "AwardAmount",
                                       "ProjectTitle", "Organization", "AgencyIcAdmin"],
                    "offset": offset, "limit": 500}).encode(),
                    headers=dict(UA, **{"content-type": "application/json"}))
                with urllib.request.urlopen(request, timeout=120) as response:
                    data = json.loads(response.read())
                rows = data.get("results") or []
                for r in rows:
                    title = r.get("project_title") or ""
                    grantee = (r.get("organization") or {}).get("org_name") or ""
                    key = r.get("appl_id")
                    if key in seen or not org.search(grantee) or not r.get("award_amount"):
                        continue
                    if not CENTRE_BIO.search(title) or routine(title):
                        continue
                    seen.add(key)
                    keep.append({"id": key, "year": r["fiscal_year"], "recipient": label,
                                 "title": "%s (NIH %s, %s %s)" % (
                                     title.strip(), ((r.get("agency_ic_admin") or {})
                                                     .get("abbreviation") or "").strip(),
                                     first, last),
                                 "amount": round(r["award_amount"])})
                offset += len(rows)
                if not rows or offset >= (data.get("meta") or {}).get("total", 0):
                    break
    require(keep, "no NIH grants passed the rule")
    keep.sort(key=lambda g: (-g["year"], str(g["id"])))
    return {
        "funder": "US NIH, for university centres",
        "funder_org": None,
        "kind": "government",
        "rule": ("NIH grants led by researchers who lead university-based centres on the map (for "
                 "example Marc Lipsitch for Harvard's CCDD, Trevor Bedford for Nextstrain), at that "
                 "university, whose title names pandemic or outbreak work, influenza or pathogen "
                 "surveillance, leaving out routine diseases. Each fiscal year's award counts. These "
                 "centres are not in the USAspending list, so no award is counted twice. A grant led by "
                 "someone else at the centre is missed."),
        "scope": "on_map_only",
        "source_url": "https://reporter.nih.gov/",
        "exported_at": None,
        "grants": keep,
    }


# ---------------------------------------------------------------- European Union (CORDIS)

CORDIS = ["https://cordis.europa.eu/data/cordis-h2020projects-csv.zip",
          "https://cordis.europa.eu/data/cordis-HORIZONprojects-csv.zip"]
USD_PER_EUR = {2014: 1.329, 2015: 1.110, 2016: 1.107, 2017: 1.130, 2018: 1.181, 2019: 1.120,
               2020: 1.142, 2021: 1.183, 2022: 1.053, 2023: 1.081, 2024: 1.082, 2025: 1.093,
               2026: 1.120}
# EU calls dedicated to epidemics name it in their topic code (SC1-PHE-CORONAVIRUS-2020)
EU_TOPIC = re.compile(r"CORONAVIRUS|COVID|EPIDEM|PANDEM|PREPAREDNESS|OUTBREAK|EBOLA|ZIKA|HERA", re.I)
upper = lambda name: re.sub(r"\s+", " ", name or "").strip().upper()


def eu_cordis():
    config = government_config()["eu"]
    label_of = {upper(n): label for label, names in config.items() for n in names}
    csv.field_size_limit(10 ** 8)
    keep = []
    for url in CORDIS:
        request = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(request, timeout=600) as response:
            book = zipfile.ZipFile(io.BytesIO(response.read()))
        read = lambda name: csv.DictReader(io.TextIOWrapper(book.open(name), encoding="utf-8"),
                                           delimiter=";")
        partners = {}
        for r in read("organization.csv"):
            label = label_of.get(upper(r.get("name")))
            money = (r.get("ecContribution") or "").replace(",", ".")
            if label and money:
                try:
                    if float(money) > 0:
                        partners.setdefault(r["projectID"], []).append((label, float(money)))
                except ValueError:
                    pass
        projects = 0
        for r in read("project.csv"):
            projects += 1
            if r["id"] not in partners:
                continue
            title = r.get("title") or ""
            if not (EU_TOPIC.search(r.get("topics") or "") or US_BIO.search(title)
                    or WELLCOME_DESC.search(r.get("objective") or "")) or routine(title):
                continue
            year = int((r.get("startDate") or "0")[:4] or 0)
            if not year:
                continue
            for label, eur in partners[r["id"]]:
                keep.append({"id": "%s|%s" % (r["id"], label), "year": year, "recipient": label,
                             "title": "%s (%s, %s)" % (title.strip(), r.get("acronym") or "",
                                                       r.get("frameworkProgramme") or ""),
                             "amount": round(eur * USD_PER_EUR.get(year, USD_PER_EUR[2026]))})
        require(projects >= 10000, "only %d projects in %s" % (projects, url))
    require(keep, "no EU projects passed the rule")
    keep.sort(key=lambda g: (-g["year"], g["id"]))
    return {
        "funder": "European Union research programmes",
        "funder_org": None,
        "kind": "government",
        "rule": ("Horizon 2020 and Horizon Europe projects, from CORDIS, that come from calls dedicated "
                 "to epidemics or preparedness, or whose title names pandemic or biodefense work, or "
                 "whose summary is plainly about pandemic preparedness or biosecurity, leaving out "
                 "routine diseases. Each organisation counts only its own share of the EU contribution, "
                 "converted to dollars at each year's average rate. Only for a hand-checked list of "
                 "organisations on the map."),
        "scope": "on_map_only",
        "source_url": "https://cordis.europa.eu/",
        "exported_at": None,
        "grants": keep,
    }


# ---------------------------------------------------------------- UK Research and Innovation

GTR = "https://gtr.ukri.org/gtr/api/"


def gtr(path):
    request = urllib.request.Request(GTR + path, headers=dict(
        UA, Accept="application/vnd.rcuk.gtr.json-v7"))
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read())


def ukri():
    config = government_config()["ukri"]
    keep, seen = [], set()
    for label, spec in sorted(config.items()):
        names = {n.lower() for n in spec["names"]}
        ids = set()
        for term in spec["search"]:
            found = gtr("organisations?q=%s&s=100" % urllib.parse.quote(term))
            ids |= {o["id"] for o in found.get("organisation") or [] if o["name"].lower() in names}
        for org_id in sorted(ids):
            page = 1
            while True:
                data = gtr("organisations/%s/projects?s=100&p=%d" % (org_id, page))
                for p in data.get("project") or []:
                    links = {}
                    for link in (p.get("links") or {}).get("link") or []:
                        links.setdefault(link["rel"], []).append(link["href"])
                    # only projects the organisation leads: the money is paid to the lead
                    if p["id"] in seen or not any(h.endswith(org_id) for h in links.get("LEAD_ORG", [])):
                        continue
                    title = p.get("title") or ""
                    if not (p.get("leadFunder") == "COVID" or US_BIO.search(title)
                            or WELLCOME_DESC.search(p.get("abstractText") or "")) or routine(title):
                        continue
                    for href in links.get("FUND", [])[:1]:
                        fund = gtr(href.split("/gtr/api/", 1)[1])
                        pounds = ((fund.get("valuePounds") or {}).get("amount") or 0)
                        if not (pounds and fund.get("start")):
                            continue
                        year = datetime.datetime.fromtimestamp(fund["start"] / 1000, datetime.timezone.utc).year
                        seen.add(p["id"])
                        keep.append({"id": p["id"], "year": year, "recipient": label,
                                     "title": "%s (%s)" % (title.strip(), p.get("leadFunder") or "UKRI"),
                                     "amount": round(pounds * USD_PER_GBP.get(year, USD_PER_GBP[2026]))})
                if page >= (data.get("totalPages") or 1):
                    break
                page += 1
    require(keep, "no UKRI projects passed the rule")
    keep.sort(key=lambda g: (-g["year"], g["id"]))
    return {
        "funder": "UK Research and Innovation",
        "funder_org": None,
        "kind": "government",
        "rule": ("Projects from UK Research and Innovation's councils and Innovate UK, from its Gateway to "
                 "Research, that the organisation leads and that came from UKRI's COVID-19 rapid response, "
                 "or whose title names pandemic or biodefense work, or whose summary is plainly about "
                 "pandemic preparedness or biosecurity, leaving out routine diseases. Pounds are "
                 "converted to dollars at each year's average rate. Only for a hand-checked list of "
                 "organisations on the map."),
        "scope": "on_map_only",
        "source_url": "https://gtr.ukri.org/",
        "exported_at": None,
        "grants": keep,
    }


SOURCES = {"coefficient_giving": coefficient_giving, "gates": gates,
           "sentinel_bio": sentinel_bio, "sff": sff,
           "openai_foundation": openai_foundation, "longview": longview,
           "wellcome": wellcome, "us_federal": us_federal, "nih_centres": nih_centres,
           "eu_cordis": eu_cordis, "ukri": ukri}


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

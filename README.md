# The Biosecurity Defence Chain

An interactive map of the biosecurity field: **168 organisations arranged as the layers
of defence a pandemic threat has to get through.**

**→ [View the map](https://shrlxmp.github.io/biosecurity-map/)**

Feedback very welcome — please open an issue, or comment on anything that looks wrong,
misplaced or missing.

## What it is

Biosecurity is built as *defence in depth*: a series of barriers, each catching what the
last one missed. The map draws that literally. A threat arrives at the outer edge and has
to cross three barriers to reach the people at the centre:

| Ring | | Orgs |
|---|---|---:|
| **Prevention** | outer — stop a dangerous agent being made or released at all | 29 |
| **Detection** | middle — spot an outbreak while containing it is still cheap | 14 |
| **Response** | inner — blunt an outbreak already spreading | 51 |
| **Foundation** | not a barrier: the funders, educators, coordinators and reporters the other three stand on | 74 |

Radius carries meaning: the further out an organisation sits, the earlier in the chain it
acts. Ring occupancy carries meaning too — **Detection is visibly the thinnest and most
widely spaced barrier**, which is the map's main finding rather than a rendering artefact.

Four views:

- **The map** — the rings, with every organisation as a clickable logo
- **Chain view** — the same four groups as labelled columns, easier to read down a list
- **Where the gaps are** — organisations per topic, plus the full 19 × 7 topic-by-work-type
  grid where empty cells show combinations nobody covers
- **How topics connect** — which topics are worked on by the same organisations

## Data

All organisation data comes from **[biosecurity.world](https://biosecurity.world/)**, which
publishes it openly ([entries.csv](https://biosecurity.world/data/entries.csv),
[source](https://github.com/biosecurity-world/biosecurity.world)). That site is the
maintained, authoritative version of this landscape and is updated weekly; this repo is a
visualisation layer over it, not a replacement or a fork of the dataset.

Snapshot in this repo: `build/entries.csv`, taken **2026-09-09**.

Logos are each organisation's own favicon, fetched once and inlined, used for
identification only.

### Reading caveats

- The rings are a **diagram, not geography**. Where a dot sits *within* a ring means
  nothing — only which ring it is in.
- Each organisation is placed **once**, at its primary classification in the dataset, so
  ring counts here run lower than the counts on biosecurity.world, which lists an
  organisation under every stage it touches.
- Counts reflect who is **catalogued** — not budget, headcount or output. A sparse ring may
  mean a genuine gap, a gap in the dataset's coverage, or a layer where a few very large
  institutions do most of the work.

## Rebuilding

The published page is a single self-contained `index.html` (~390 KB) with the data and all
logos inlined. No build step is needed to host it; GitHub Pages serves the file directly.

To regenerate it:

```bash
python build/fetch_logos.py          # refresh cached favicons -> build/logos.json
python build/build.py                # rebuild index.html from build/entries.csv
python build/build.py --refresh      # re-download entries.csv from biosecurity.world first
```

`build/template.html` is the page with `__ORGS__` / `__LOGOS__` placeholders where the data
is injected. Edit the template, not `index.html` — `index.html` is generated and will be
overwritten.

Requires Python 3 only; no dependencies.

## Licence

Code in this repository: MIT (see `LICENSE`).

Organisation data belongs to biosecurity.world and its contributors — please credit them,
not this repo, as the source. Logos are the property of the respective organisations.

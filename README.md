# The Biosecurity Defence Chain

An interactive map of the biosecurity field: **168 organisations arranged as the layers
of defence a pandemic threat has to get through.**

**→ [View the map](https://shrlxmp.github.io/biosecurity-map/)**

Feedback very welcome — please open an issue, or comment on anything that looks wrong,
misplaced or missing.

## What it is

Biosecurity is built as *defence in depth*: a series of barriers, each catching what the
last one missed. The map draws the whole field as **one island**, and the coastline is
generated rather than drawn — every organisation contributes to a scalar field whose
waterline becomes the shore. So the land takes its shape from where the organisations
actually are: a crowded part of the field is a genuinely wider province, a neglected one a
genuinely narrower spit.

The island reads **west to east**, in the order a threat is met:

| Province group | | Orgs |
|---|---|---:|
| **Prevention** | the western shore, where a threat makes landfall — stop an agent being made or released at all | 29 |
| **Detection** | the narrows — spot an outbreak while containing it is still cheap | 14 |
| **Response** | the eastern interior — blunt an outbreak already spreading | 51 |
| **Foundation** | the southern plain — funders, teachers, coordinators and reporters; not a stage, but what the rest stands on | 74 |

Thirteen named places sit inside those four, one per sub-category: Containment Coast,
Infohazard Bluff, Sentinel Watch, Assay Point, The Narrows, Countermeasure Basin, Clean Air
Commons, Readiness Plain, Treaty Cape, Fellows' Field, Signal Shore, Funders' Harbour and
Concord Table.

Because area is generated from the data, **Detection is visibly a narrow isthmus** — 14
organisations against 51 in the Response interior. The cheapest place to stop a pandemic is
the thinnest stretch of the map.

Four views:

- **The map** — the island, with every organisation as a clickable logo
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

Snapshot in this repo: `build/entries.csv`, refreshed weekly by the workflow below.

Logos are each organisation's own favicon, fetched once and inlined, used for
identification only.

### Reading caveats

- The island is a **diagram, not geography**. Where an organisation sits *within* its
  province means nothing — only which province it is in. The provinces are arranged to
  follow the defence chain, not to describe anywhere real.
- Each organisation is placed **once**, at its primary classification in the dataset, so
  province counts here run lower than the counts on biosecurity.world, which lists an
  organisation under every stage it touches.
- Counts reflect who is **catalogued** — not budget, headcount or output. A narrow province
  may mean a genuine gap, a gap in the dataset's coverage, or a stage where a few very
  large institutions do most of the work.

## Staying current

The map **refreshes itself weekly**. A scheduled GitHub Actions workflow
(`.github/workflows/refresh.yml`) runs every Monday: it pulls the latest `entries.csv` from
biosecurity.world, fetches logos for any newly listed organisations, rebuilds `index.html`,
and commits only if something actually changed. GitHub Pages redeploys automatically.

It can also be run on demand from the **Actions** tab → *Refresh map from biosecurity.world*
→ *Run workflow*.

Downloads are validated for schema and row count before `entries.csv` is overwritten, so a
moved URL or an error page fails the run loudly rather than quietly publishing an empty map.

## Rebuilding by hand

The published page is a single self-contained `index.html` (~390 KB) with the data and all
logos inlined. No build step is needed to host it; GitHub Pages serves the file directly.

To regenerate it locally:

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

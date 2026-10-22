# The Biosecurity Defence Chain

An interactive map of the biosecurity field: **every organisation in the
[biosecurity.world](https://biosecurity.world/) dataset, arranged as the layers of defence a
pandemic threat has to get through.**

**→ [View the map](https://shrlxmp.github.io/biosecurity-map/)**

Feedback is very welcome. Please open an issue about anything that looks wrong, misplaced or
missing.

## What it is

Biosecurity is built as *defence in depth*: a series of barriers, each catching what the
last one missed. The map draws that literally. A threat has to cross three barriers to reach
the people at the centre.

| Ring | What it does |
|---|---|
| **Prevention** | Outer barrier. Stops a dangerous agent being made or released at all. |
| **Detection** | Middle barrier. Spots an outbreak while containing it is still cheap. |
| **Response** | Inner barrier. Slows an outbreak that is already spreading. |
| **Foundation** | Dashed outermost ring, not a barrier. The funders, educators, coordinators and reporters the other three rely on. |

Across the three barriers, radius carries meaning: the further out an organisation sits, the
earlier in the chain it acts. Each organisation sits on one ring only, the one for its main
mission. By that count Detection has the fewest organisations of the three barriers, but many
more organisations on other rings work on detection topics such as pathogen surveillance. The
page shows both numbers and works them out from the data on every build, so the counts and
the claims stay true after each refresh.

There are four views:

- **The map.** The rings, with every organisation as a clickable logo.
- **Chain view.** The same four groups as columns of names, easier to read down.
- **Where the gaps are.** Organisations per topic, plus the full grid of topics against types
  of work, where empty cells show combinations nobody covers.
- **How topics connect.** Which topics are worked on by the same organisations.

## Data

All organisation data comes from **[biosecurity.world](https://biosecurity.world/)**, which
publishes it openly ([entries.csv](https://biosecurity.world/data/entries.csv),
[source](https://github.com/biosecurity-world/biosecurity.world)). That site is the
maintained, authoritative version of this landscape and is updated weekly. This repo is a
visualisation built on top of it, not a replacement or a fork of the dataset.

The snapshot in this repo is `build/entries.csv`, refreshed weekly by the workflow below.

Newsletters and podcasts listed in the dataset (entries named `Newsletter - …` or
`Podcast - …`) are left off the map. They are publications rather than organisations, and
most repeat an organisation that is already on it. `build.py` drops them at build time, and
`entries.csv` keeps them.

Logos are each organisation's own favicon, fetched once and inlined, and used for
identification only.

### Reading caveats

- The rings are a **diagram, not geography**. Where a dot sits *within* a ring means
  nothing, only which ring it is in.
- Each organisation is placed **once**, at its primary classification in the dataset, so
  ring counts here run lower than the counts on biosecurity.world, which lists an
  organisation under every stage it touches. A thin ring means few organisations whose
  *main* mission is that stage, not that little work happens there.
- Counts show who is **catalogued**, not budget, headcount or output. A sparse ring may be a
  real gap, a gap in the dataset's coverage, or a layer where a few very large institutions
  do most of the work.

## Staying current

The map **refreshes itself weekly**. A scheduled GitHub Actions workflow
(`.github/workflows/refresh.yml`) runs every Monday. It pulls the latest `entries.csv` from
biosecurity.world, fetches logos for any newly listed organisations, rebuilds `index.html`,
and commits only if something changed. GitHub Pages then redeploys on its own.

You can also run it on demand from the **Actions** tab → *Refresh map from biosecurity.world*
→ *Run workflow*.

Downloads are checked for the expected columns and row count before `entries.csv` is
overwritten, so a moved URL or an error page makes the run fail instead of publishing an
empty map.

## Rebuilding by hand

The published page is a single self-contained `index.html` with the data and all logos
inlined. Hosting it needs no build step, because GitHub Pages serves the file directly.

To regenerate it locally:

```bash
python build/fetch_logos.py          # refresh cached favicons -> build/logos.json
python build/build.py                # rebuild index.html from build/entries.csv
python build/build.py --refresh      # re-download entries.csv from biosecurity.world first
```

`build/template.html` is the page with `__ORGS__`, `__LOGOS__` and `__COUNT__` placeholders
where the data goes. Edit the template, not `index.html`, which is generated and gets
overwritten.

The build needs Python 3 only, with no dependencies.

## Licence

Code in this repository: MIT (see `LICENSE`).

Organisation data belongs to biosecurity.world and its contributors. Please credit them, not
this repo, as the source. Logos are the property of the respective organisations.

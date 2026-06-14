# External OpenSCAD corpus — sources

Real-world, open-source `.scad` projects used to stress the CSG→STEP importer
beyond the hand-written `csg_tests/` cases. Surveyed 2026-06-12 (openscad.org
gallery, GitHub, awesome-openscad lists, Thingiverse/Printables/Cults3D).

Nothing here is committed to the repo: `fetch_and_compile.py` downloads the
direct sources into an untracked work dir and compiles them to `.csg`
(`openscad -o x.csg x.scad` — AST compile only, fast). The pipeline then runs
them like any other corpus:

```sh
python3 csg_tests/external/fetch_and_compile.py            # → ./csg_external/{repos,single,csg}
python3 src/Mod/OpenSCAD/csg_isolation/run_all.py  --tests csg_external/csg --out csg_external/out
python3 src/Mod/OpenSCAD/csg_isolation/validate.py --tests csg_external/csg --out csg_external/out
```

Compile-time notes: the harness was exercised with **OpenSCAD 2021.01**.
Files needing newer language features fail at the *openscad compile* step
(recorded `compile-error` in `csg/harvest.json` — not an importer defect).
Pure-library files that produce no top-level geometry are skipped (`empty`).

## Tier 1 — direct fetch, used by fetch_and_compile.py

| Source | What we take | License | Notes |
|---|---|---|---|
| [openscad/openscad](https://github.com/openscad/openscad) | `examples/{Basics,Advanced,Parametric,Old}` | CC0 | curated, renderable |
| [openscad/openscad](https://github.com/openscad/openscad) | `tests/data/scad/2D/features/*` | GPL-2+ | upstream 2D regression corpus (booleans, offset, hull2, minkowski2); `text-*` excluded (font deps) |
| [openscad/openscad](https://github.com/openscad/openscad) | `tests/data/scad/3D/features/*` | GPL-2+ | upstream 3D corpus; `import*`/`surface*`/`text*` excluded (file/font I/O, not CSG) |
| [adereth/dactyl-keyboard](https://github.com/adereth/dactyl-keyboard) | `things/dactyl-top-right.scad` | AGPL-3 | 4.5 MB machine-generated union/diff/hull tree — parser+BOP stress |
| [rcolyer/threads-scad](https://github.com/rcolyer/threads-scad) | `threads.scad` | CC0 | polyhedron-built thread helices |
| [jbebel/Ultimate-Box-Maker](https://github.com/jbebel/Ultimate-Box-Maker) | `files/Ultimate_Box.scad` | CC BY-NC 3.0 | classic parametric enclosure (offset/extrude heavy) |
| [prusa3d/Original-Prusa-i3](https://github.com/prusa3d/Original-Prusa-i3) (branch `MK3S`) | `Printed-Parts/SCAD/*` | GPL-2 | 23 production printer parts, self-contained |
| [kennetek/gridfinity-rebuilt-openscad](https://github.com/kennetek/gridfinity-rebuilt-openscad) | top-level entry models | MIT | `gridfinity-rebuilt-bins.scad` needs OpenSCAD > 2021.01 (syntax error on 2021.01) |
| [jeffbarr/OpenSCADObjects](https://github.com/jeffbarr/OpenSCADObjects) | all 28 objects | MIT | simple/moderate customizer objects — easy tier |
| [Irev-Dev/Round-Anything](https://github.com/Irev-Dev/Round-Anything) | `roundAnythingExamples.scad`, `examples/*` | MIT | polygon-math + minkowski rounding |
| [rsheldiii/KeyV2](https://github.com/rsheldiii/KeyV2) | `keys.scad`, `examples/*` | GPL-3 | hull-heavy keycap geometry |
| [dpellegr/PolyGear](https://github.com/dpellegr/PolyGear) | `examples/*` | CC BY-SA 4.0 | polyhedron gear math (most examples are library-guarded → `empty` on 2021.01) |
| [openscad/MCAD](https://github.com/openscad/MCAD) | `involute_gears.scad`, `boxes.scad`, `bearing.scad` | LGPL-2.1 | demo modules are guarded → currently `empty`; needs a small driver .scad to instantiate |

More direct leads (not yet harvested): [openscad-lists
gallery.yaml](https://raw.githubusercontent.com/openscad/openscad-lists/main/data/gallery.yaml)
(machine-readable model list), [NopSCADlib](https://github.com/nophead/NopSCADlib)
`tests/` (148 single-purpose renderables, GPL-3, needs itself on
`OPENSCADPATH`), [BOSL2](https://github.com/BelfrySCAD/BOSL2) `examples/`
(BSD-2), [dotSCAD](https://github.com/JustinSDK/dotSCAD) `examples/` (212
generative-art files, LGPL-3), [jazwa/rackstack](https://github.com/jazwa/rackstack)
(MIT, 100-file assembly), [eclecticc/ParametricCase](https://github.com/eclecticc/ParametricCase)
(BSD-2), [oskitone/poly555](https://github.com/oskitone/poly555) (CC BY-SA 3.0),
[carlosgs/Cyclone-PCB-Factory](https://github.com/carlosgs/Cyclone-PCB-Factory)
(CC BY-SA 3.0, vendors its libs), [Metamaquina2](https://github.com/Metamaquina/Metamaquina2)
(GPL-3), [nophead/Mendel90](https://github.com/nophead/Mendel90) (GPL-2,
needs its Python config harness), [hugs/tapsterbot](https://github.com/hugs/tapsterbot)
(BSD-3), [ubitux/shimonbox](https://github.com/ubitux/shimonbox) (ISC),
[paulirotta/PELA-blocks](https://github.com/paulirotta/PELA-blocks) (CC BY-SA 4.0),
[martinbudden/BabyCube](https://github.com/martinbudden/BabyCube) (CC BY-**NC**-SA,
needs NopSCADlib).

## Tier 2 — one step away (needs an interactive browser)

These hosts block non-interactive access (Cloudflare/captcha/login). Open the
URL in a browser, download the `.scad` (login may be needed), drop the files
into `csg_external/single/`, re-run `fetch_and_compile.py`.

**Thingiverse** — every `thing:` page is a JS shell + 403 API for headless
clients; the anonymous "download all" zip redirects to login. *Workaround:*
once a page is open in a browser, the per-file
`https://www.thingiverse.com/download:<ID>` links (visible on the Files tab)
DO work headlessly via curl afterwards (verified: 302 → cdn.thingiverse.com →
200, no cookies).

| Design | URL | License |
|---|---|---|
| Gear Bearing (print-in-place planetary, emmett) | https://www.thingiverse.com/thing:53451 | CC BY-SA 3.0 |
| Screwless Cube Gears (emmett) | https://www.thingiverse.com/thing:10483 (v2: thing:213946) | CC BY-SA |
| Stretchy Bracelet (emmett) | https://www.thingiverse.com/thing:13505 | CC BY-SA |
| NUT JOB nut/bolt/washer/rod factory (mike_mattala) | https://www.thingiverse.com/thing:193647 | unverified |
| Parametric pulley (droftarts) | https://www.thingiverse.com/thing:16627 | unverified |
| Threading.scad (Parkinbot) | https://www.thingiverse.com/thing:1659079 | unverified |
| Tool Holder parametric (benglish) | https://www.thingiverse.com/thing:13511 | unverified |
| The Ultimate box maker (Heartman) | https://www.thingiverse.com/thing:1264391 | CC BY-NC 3.0 |
| Advanced Ultimate Box Maker (M-oster) | https://www.thingiverse.com/thing:4947863 | CC BY-NC |
| Passive Rider / Digital Marionette (gallery item, Thingiverse-only) | https://www.thingiverse.com/thing:6232798 | CC BY-SA 4.0 |

**Printables** — pages and file lists readable headlessly; the binary download
itself needs a session. File names below verified present:

| Design | URL | .scad verified |
|---|---|---|
| Gridfinity Extended OpenSCAD (Ostat) | https://www.printables.com/model/630057-gridfinity-extended-openscad | 8 files (`gridfinity_basic_cup.scad`, …) |
| Gridfinity OpenSCAD Model (Jamie) | https://www.printables.com/model/174346-gridfinity-openscad-model | 7 files |
| Parametric Planetary Gearbox (Rodryk) | https://www.printables.com/model/286744-parametric-planetary-gearbox-openscad | `planetary_gearbox.scad` (46 kB) |
| Parametrizable Rugged Box (Dochni) | https://www.printables.com/model/168664-parametrizable-rugged-box-openscad | yes |
| Simple customizable Box (fatdavemakes) | https://www.printables.com/model/40318-simple-customizable-box-parametric-openscad | yes |
| Parametric box generator (Milan8) | https://www.printables.com/model/1240246-fully-parametric-box-generator-in-openscad | in zip |
| Sortimo L-BOXX inserts (UnleashSpirit) | https://www.printables.com/model/979554-sortimo-inset-boxes-l-boxx-customizable | `sortimo_insert.scad` |

**Cults3D** — readable pages, download needs a free account:
[The Ultimate box maker](https://cults3d.com/en/3d-model/tool/the-ultimate-box-maker)
(2 .scad), [Advanced Ultimate Box Maker](https://cults3d.com/en/3d-model/gadget/advanced-ultimate-box-maker)
(9 .scad). **MakerWorld** — fully blocked (403):
[NUT JOB mirror](https://makerworld.com/en/models/55381-nut-job-nut-bolt-washer-and-threaded-rod-factory).

Note GitHub already mirrors several Thingiverse hits, so the browser trip is
only needed for the rest: Ultimate Box Maker → `jbebel/Ultimate-Box-Maker`,
PolyGear → `dpellegr/PolyGear`, NUT JOB → `Nut_Job.scad` inside
`mariolukas/openexposer`, Ultimate Drawer System →
`ALittleSlow/Ultimate-Drawer-System`, Gridfinity Extended →
`ostat/gridfinity_extended_openscad`.

## Dead ends (gallery items with no reachable source)

- *Koke quadruped* — schpin.org offline; source was on a university GitLab,
  now login-walled; only STL exports survive on web.archive.org.
- *VW Beetle motorization* — simulationrc.com offline, source never published.

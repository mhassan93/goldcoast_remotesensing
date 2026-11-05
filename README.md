# Gold Coast Remote Sensing

An interactive web map of the City of Gold Coast local government area, the study area for a remote sensing portfolio project.

- **Live site:** https://mhassan93.github.io/goldcoast_remotesensing/
- **Repository:** https://github.com/mhassan93/goldcoast_remotesensing

- **Milestone 1** set up the base map: the official LGA boundary drawn over an OpenFreeMap street basemap, with pan, zoom and a **Reset to Gold Coast** button.
- **Milestone 2** adds a **Terrain** toggle for subtle hillshading from Mapterhorn elevation tiles.
- **Milestone 3** adds a **Land cover** panel. It shows Digital Earth Australia's annual 30 m Level 3 land cover for 2010 or 2025, with a legend and an opacity slider.
- **Milestone 4** turns the panel into an **Analysis layer** panel. It also offers this project's own 2025 Sentinel-2 outputs: an index-rule classification and NDVI, NDBI and MNDWI composites at 20 m. A reproducible Python pipeline in [`analysis/`](analysis) produces them, and [docs/spectral-indices.md](docs/spectral-indices.md) documents the method, checks and assessment.

The site is a static single-page app built with React, TypeScript, Vite and MapLibre GL JS. It needs no server-side code or API keys, so it can be hosted on any static host, including GitHub Pages.

## Requirements

- Node.js 20.19+ or 22.12+, which includes npm. It is developed and tested on Node 26.13.
- A modern browser with WebGL 2 (current Chrome, Edge, Firefox or Safari)
- An internet connection for the basemap, elevation and DEA land cover tiles (the Sentinel-2 layers are served from `public/`)
- Only to rerun the Sentinel-2 pipeline: Python 3.13 and about 5 GB of free disk space (a 4.2 GB working folder and a 0.2 GB environment). The download is about 6.4 GB. See [docs/spectral-indices.md](docs/spectral-indices.md#reproducing-the-pipeline-powershell)

## Run locally (PowerShell)

From the project folder (the repository root):

```powershell
npm.cmd install
npm.cmd run dev
```

Open the URL Vite prints, normally http://localhost:5173/. Press `Ctrl+C` in the terminal to stop the server. `npm install` is only needed the first time, or after dependencies change.

To check the production build locally:

```powershell
npm.cmd run build
npm.cmd run preview
```

`npm run preview` serves the built `dist/` folder, normally at http://localhost:4173/.

Before reinstalling dependencies (`npm install` or `npm ci`), stop any running `dev` or `preview` server. A running server keeps Rolldown's native file open, and Windows will not let npm replace a file that is in use.

## Deploy to GitHub Pages

[.github/workflows/deploy-pages.yml](.github/workflows/deploy-pages.yml) publishes the site with GitHub Actions. It runs on every push to `main`, and can also be started from the repository's **Actions** tab.

1. **Build job.** It checks out the repository without keeping the Git token, sets up Node 26 and reads the Pages settings with `actions/configure-pages`. It then installs the locked dependencies with `npm ci --ignore-scripts` and runs `npm run build`. No package needs an install script on Linux; the only one in the lockfile is the macOS-only `fsevents`.
2. **Base path.** The build passes the site's base path to Vite as `PAGES_BASE_PATH` (for a project site, `/<repository-name>`). Every app file, tile and data request then starts with that path, whatever the repository is called.
3. **Deploy job.** It uploads `dist/` and deploys it to the `github-pages` environment.

**Workflow security.**
- **Branch:** both jobs run only for `refs/heads/main`, including manual runs.
- **Token permissions:** the workflow grants none by default. The build job gets `contents: read` (checkout) and `pages: read` (`configure-pages` reads the site settings). Only the deploy job gets `pages: write` and `id-token: write`, which `deploy-pages` uses to deploy with a short-lived OIDC token. No secrets or long-lived deployment keys are used.
- **Pinned actions:** every action is pinned to the full commit SHA of a signed release:

  | Action | Release |
  | --- | --- |
  | `actions/checkout` | v7.0.1 |
  | `actions/setup-node` | v7.1.0 |
  | `actions/configure-pages` | v6.0.0 |
  | `actions/upload-pages-artifact` | v5.0.0 |
  | `actions/deploy-pages` | v5.0.1 |

  To update one, look up the new release's commit SHA on its GitHub releases page and replace the pin.

**Zero-spend controls.** The workflow is set up to cost nothing on GitHub Free:
- **Public repositories only.** Both jobs are skipped if the repository is private, so no runner time is used there.
- **Free runners.** Both jobs use `ubuntu-latest`, a standard GitHub-hosted runner, which GitHub documents as free in public repositories.
- **One short-lived artifact.** The Pages artifact (about 12 MB compressed) is kept for one day (`retention-days: 1`).
- **Nothing else billable.** There is no dependency cache (`package-manager-cache: false`), no other artifact, no package publishing, no Git LFS, no service containers and no secrets.

In the account's billing settings, a budget with **Stop usage when budget limit is reached** and a $0 amount guards against anything else.

**Repository settings.** The repository is **Public** with `main` as its default branch. In **Settings → Pages → Build and deployment**, **Source** is **GitHub Actions**. In **Settings → Environments → github-pages**, deployment branches are limited to `main`. A copy of the project in another repository needs the same three settings before its first push. Protecting `main` in **Settings → Rules** is optional.

**Updating the site.** Every push to `main` rebuilds the site from that commit and replaces the live version, usually within a few minutes. Progress and logs are in the **Actions** tab. Pushes to other branches do not deploy. If a run fails, the previous version stays live.

**What is published.** Only `dist/` is published: the app, the boundary file, the Sentinel-2 tiles and `third-party-licenses.txt`, about 14 MB in 880 files. The largest file is the 1.3 MB JavaScript bundle, well under GitHub Pages' 1 GB site limit. The imagery cache, Python environment, `node_modules` and build output are excluded by `.gitignore` and never committed.

To test a Pages build locally under a subpath (PowerShell), use the repository name in place of `goldcoast_remotesensing`:

```powershell
$env:PAGES_BASE_PATH = "/goldcoast_remotesensing"
npm.cmd run build
npm.cmd run preview
Remove-Item Env:PAGES_BASE_PATH
```

Open http://localhost:4173/goldcoast_remotesensing/ while the preview runs. Without `PAGES_BASE_PATH`, the build serves from `/` as before.

## npm scripts

| Script | What it does |
| --- | --- |
| `npm run dev` | Starts the Vite development server with instant reload on file changes |
| `npm run build` | Type-checks with TypeScript (`tsc -b`), then writes an optimised static site to `dist/` |
| `npm run preview` | Serves `dist/` locally so the production build can be tested |
| `npm run typecheck` | Runs only the TypeScript checks |
| `npm run data:boundary` | Downloads the Gold Coast boundary again from the Queensland Government service and rewrites `public/data/gold-coast-boundary.geojson` |

## Project structure

```
LICENSE                            MIT licence for this project's own code
index.html                         Page shell that Vite serves and builds from
vite.config.ts                     Vite settings: GitHub Pages base path, production CSP and third-party licence file
.github/workflows/deploy-pages.yml Builds the site and deploys it to GitHub Pages
public/
  favicon.svg                      Browser tab icon
  data/gold-coast-boundary.geojson Official City of Gold Coast boundary (generated)
  data/sentinel2-2025/             Sentinel-2 class and index tiles (zooms 8-13) and layers.json (generated)
analysis/
  config.toml                      Imagery source, grid, masks, compositing, thresholds and web styling
  requirements.txt                 Pinned Python packages for the pipeline
  samples.csv                      Calibration and assessment sample locations with reference labels
  spectral_indices/                Pipeline stages: plan, acquire, composite, calibrate, classify, verify, export, assess
  results/                         Processing manifest, verification, calibration and assessment tables
  work/                            Downloaded imagery cache and intermediates (not tracked)
scripts/
  extract-gold-coast-boundary.mjs  Node script that produces the boundary file
src/
  main.tsx                         Entry point: loads CSS, configures the MapLibre worker, mounts React
  App.tsx                          Page layout: header and map area
  components/GoldCoastMap.tsx      Creates, controls and cleans up the map; toolbar, terrain and analysis layer state, messages
  components/AnalysisLayerPanel.tsx Analysis layer panel: show switch, source, year or view, opacity, smooth display, status, legends and source notes
  map/basemap.ts                   OpenFreeMap style URL
  map/deaLandCover.ts              DEA Land Cover years, Level 3 classes and colours, service URL, attribution
  map/sentinelIndexLayers.ts       Loads layers.json and builds the Sentinel-2 tile URLs and attribution
  map/analysisLayers.ts            One raster source and layer per DEA year or Sentinel-2 view, placement and show/hide/opacity/smoothing helpers
  map/boundary.ts                  Loads the boundary file and calculates its bounding box
  map/boundaryOutline.ts           Adds the boundary source and outline layer to the map
  map/regionalFraming.ts           Padding rules shared by the startup view and the reset button
  map/terrainShading.ts            Elevation source, hillshade layer, layer placement and show/hide helpers
  map/maplibreWorker.ts            Tells MapLibre where Vite put its web worker file
  styles.css                       Page layout, toolbar, toggle switches, analysis layer panel and notice styling
docs/boundary-data.md              Boundary source, licence, extraction and decisions
docs/terrain-shading.md            Elevation provider, coverage, attribution, shading settings and failure handling
docs/land-cover.md                 DEA service, version, year parameter, verification, classes, processing and limitations
docs/spectral-indices.md           Sentinel-2 source, masks, compositing, rule, thresholds, assessment, verification and reproduction
```

## Licence

This project's own code is released under the [MIT licence](LICENSE), © 2026 Muhammad Hassan Maqsood. That covers the web app in `src/`, `index.html`, the build and workflow configuration, `scripts/`, and the Python pipeline in `analysis/spectral_indices/` with its `config.toml`.

The MIT licence does not cover anything made by others:
- **Libraries.** npm packages keep their own licences: MapLibre GL JS is BSD-3-Clause, and React, React DOM and Scheduler are MIT. Each build writes their licence texts to `third-party-licenses.txt`, which is published with the site. The Python packages in `analysis/requirements.txt` keep their own licences too.
- **Data and map services.** The boundary, basemap, elevation and DEA land cover remain under their providers' terms, listed under *Data and attribution* below. Map tiles loaded from the services are not part of this repository.
- **Data products derived from Sentinel-2.** The Sentinel-2 tiles in `public/data/sentinel2-2025/` and the tables in `analysis/results/` contain modified Copernicus Sentinel data. Any reuse must keep the credit "Contains modified Copernicus Sentinel data 2025". The project's sample labels in `analysis/samples.csv` were made by looking at third-party imagery, and none of that imagery is included.

## Data and attribution

- **Study area boundary:** *Local government area boundaries – Queensland*, © State of Queensland (Department of Natural Resources and Mines, Manufacturing and Regional and Rural Development) 2026, released under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Source: https://www.data.qld.gov.au/dataset/local-government-area-boundaries-queensland. The geometry is the full official outline with nothing simplified or removed. See [docs/boundary-data.md](docs/boundary-data.md) for how it was extracted and checked.
- **Basemap:** [OpenFreeMap](https://openfreemap.org/) "Liberty" style, © [OpenMapTiles](https://openmaptiles.org/), data © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors.
- **Elevation (Terrain toggle):** [Mapterhorn](https://mapterhorn.com/) terrain tiles, attributed as "© Mapterhorn" with a link to https://mapterhorn.com/attribution. Around the Gold Coast, Mapterhorn builds its tiles from Geoscience Australia's *Digital Elevation Model (DEM) of Australia derived from LiDAR 5 Metre Grid* (CC BY 4.0) and Copernicus GLO-30 (Copernicus licence). See [docs/terrain-shading.md](docs/terrain-shading.md).

- **Land cover:** [DEA Land Cover (Landsat)](https://knowledge.dea.ga.gov.au/data/product/dea-land-cover-landsat/) version 2.0.0, Level 3, © Commonwealth of Australia (Geoscience Australia), released under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Citation: DEA Land Cover 30m. Geoscience Australia, Canberra. https://doi.org/10.26186/149976. The tiles come from DEA's public map service, layer `ga_ls_landcover_c3`, style `level3`, with `Time=2010-01-01` or `Time=2025-01-01`. See [docs/land-cover.md](docs/land-cover.md).

- **Sentinel-2 analysis (this project):** derived from Copernicus Sentinel-2 Level-2A surface reflectance (Collection 1), read from Element 84's Earth Search catalogue on AWS. Credit line: "Contains modified Copernicus Sentinel data 2025". The classification and index composites are this project's own analysis, not a DEA or ESA product. See [docs/spectral-indices.md](docs/spectral-indices.md).

The map shows its attributions in full in the bottom-right corner, including on narrow screens. "© Mapterhorn" appears whenever terrain shading is on. The DEA Land Cover line appears whenever a DEA layer is shown, and the Sentinel-2 credit whenever one of this project's layers is shown.

## How the map behaves

- **Startup framing.** The app first downloads the boundary file and calculates its bounding box. It then creates the map with that box as its starting view, plus padding. The padding is 6% of the map's shorter side, kept between 16 and 48 px. The top also clears the toolbar (at least 48 px), and the bottom gets an extra 28 px to clear the attribution.
- **Reset.** **Reset to Gold Coast** fits the same bounding box with the same padding rule. It also returns bearing (rotation) and pitch (tilt) to zero. If the window has been resized, the padding is recalculated for the new size, so the framing stays consistent.
- **Terrain.** Terrain starts off.
  - **Switching it on** adds gentle hillshading under the roads, labels and boundary. Elevation data is only downloaded the first time it is switched on.
  - **The view never moves.** The map stays top-down and toggling never changes position, zoom, rotation or tilt.
  - **If elevation tiles cannot be loaded,** the toggle switches back off, a short notice says terrain shading is unavailable, and the street map carries on as normal. Pressing Terrain again retries.
- **Analysis layer.** The panel under the toolbar shows one analysis raster at a time. It starts with DEA land cover shown, 2025 selected, 70% opacity and smooth display on.
  - **Source.** Choose **DEA Land Cover** (published, 30 m) or **Sentinel-2 indices** (this project, 20 m). Each source remembers its own year or view.
  - **Year or view.** For DEA, choose 2010 or 2025. For Sentinel-2, choose Classes, NDVI, NDBI or MNDWI. The layer swaps in place and the map never moves.
  - **Show.** The **Show** switch hides or shows the layer.
  - **Opacity.** The slider sets how strongly the colours cover the basemap and terrain.
  - **Smooth display.** On by default, it softens the edges between raster pixels by blending neighbouring colours on screen. Switch it off to see each pixel exactly, in its own class or index colour. It applies to every analysis layer and only changes how pixels are drawn, never the data. The map, layer, year or view and opacity stay as they are.
  - **Legend and source.** For DEA, this section lists the six Level 3 classes, the source and licence, and a note on the displayed extent. For Sentinel-2 it shows the class legend or a colour scale with the formula, what transparent pixels mean, the observation period, the number of acquisitions and the 20 m resolution. It starts open on larger screens and closed on small ones.
  - **Status.** The panel says when a layer is loading, when tiles fail (with **Try again**), and when the map is zoomed out too far: below zoom 7 for DEA, or below zoom 8 for Sentinel-2.
  - **Extent.** DEA's layer covers all of Australia, so colours continue past the Gold Coast boundary and out to sea. The Sentinel-2 layers stop at the boundary.
- **Free movement.** The map has no maximum bounds, so you can pan and zoom well outside the Gold Coast for context.
- **Controls.** Reset and Terrain are top left with the Analysis layer panel below them, and zoom and compass buttons are top right. A metric scale bar sits above the attribution at bottom right. Mouse, touch (drag and pinch) and keyboard all work.
  - **Keyboard order:** Tab reaches Reset, then Terrain (Space or Enter toggles it), then the analysis controls (Show, the Source group, the Year or View group, Opacity, Smooth display, Legend and source), then the map itself. Arrow keys change the choice inside a group and the value on the slider.
  - **On the map:** the arrow keys pan and `+` / `-` zoom.
  - **Screen readers** announce Terrain, "Show analysis layer" and Smooth display as toggle buttons that are pressed or not pressed, and read the blending note with Smooth display. Source, Year and View are radio groups. Loading and errors are announced through live regions.

## Technical notes

- **MapLibre worker.** MapLibre GL JS 6 runs tile processing in a web worker loaded from a separate file, `maplibre-gl-worker.mjs`. By default it looks for that file next to its own script, which breaks under Vite in both development and production. [src/map/maplibreWorker.ts](src/map/maplibreWorker.ts) imports the file with Vite's `?url` suffix, which gives the file's real served address, and passes that to `setWorkerUrl`.
- **React StrictMode.** In development, React deliberately mounts components twice to expose missing cleanup. The map component's cleanup cancels the first boundary request and removes any map it created. That is why the browser's Network tab shows one cancelled boundary request in `npm run dev`. This does not happen in the production build.
- **Map error handling.** The map listens for MapLibre `error` events. Errors from the elevation source switch terrain shading off and show the notice. Errors from an analysis layer's source show the panel's failure message when that layer is selected. Every other error is still written to the browser console, the same as before the listener existed.
- **Smooth display.** The switch sets MapLibre's `raster-resampling` paint property on every analysis layer: `linear` when on, `nearest` when off. Vector layers (roads, labels, the Gold Coast outline) are not raster layers and are unaffected. Three settings stay the same in both states so that "off" shows exact pixel colours:
  - every analysis source chooses tiles by rounding the zoom down, so tiles are never shrunk on screen
  - the map never turns on anisotropic filtering (`anisotropicFilterPitch: 180`), which MapLibre would otherwise leave on for tiles drawn while tilted
  - the DEA and Sentinel-2 class layers do not fade tiles in

  [docs/land-cover.md](docs/land-cover.md#smooth-display-and-exact-class-colours) gives the reasons and measurements, including the faint tile-edge lines that smoothing leaves at zoom 16 and beyond.
- **Bundle size warning.** `npm run build` warns that the JavaScript chunk is over 500 kB. Almost all of it is MapLibre GL JS (about 1.25 MB minified, 348 kB gzipped). This is normal for a WebGL map library, and the warning is left visible rather than hidden.
- **Console warnings from the basemap style.** OpenFreeMap's Liberty style logs three warnings about highway-shield layer filters (`Expected value to be of type number, but found null`). At high zoom it can also warn that the image "swimming_pool" could not be loaded. These come from the hosted style, not from this project, and do not affect the map.
- **Content Security Policy.** The production `index.html` carries a CSP `<meta>` tag, which `vite.config.ts` adds at build time only, because the development server needs inline scripts. The policy allows scripts, styles and fonts only from the site itself. It allows network requests only to the site and the three map services (OpenFreeMap, Mapterhorn and DEA). GitHub Pages cannot send custom response headers, so the policy has to live in the page itself. Policies in a `<meta>` tag cannot set `frame-ancestors` and do not cover the MapLibre worker's own requests.
- **Attribution text.** MapLibre sanitises attribution HTML before showing it. On top of that, the Mapterhorn attribution is a fixed string in the app rather than the text from Mapterhorn's TileJSON, and the Sentinel-2 credit from `layers.json` is escaped as plain text.
- **Dependency versions** are pinned exactly in `package.json`, and `package-lock.json` locks every transitive dependency. Milestones 2 to 4 added no web dependencies. Hillshading and raster tile layers are built into MapLibre, and both DEA's and this project's tiles arrive ready-coloured. The Python pipeline pins its own packages in `analysis/requirements.txt` (numpy, rasterio with its bundled GDAL, pyproj, Pillow and their dependencies). Its virtual environment and imagery cache are not tracked.

## Scope

Milestones 1 to 4 cover the local map, 2D terrain shading, the 2010 and 2025 DEA land cover layers, and this project's 2025 Sentinel-2 index analysis. The display smoothing switch and the GitHub Pages workflow have been added since. Land cover area statistics, change maps, charts and pixel inspection come next. 3D terrain, elevation readouts and satellite imagery are planned for later milestones.

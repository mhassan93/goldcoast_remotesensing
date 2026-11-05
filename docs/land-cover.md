# Land cover

The **Analysis layer** panel shows Digital Earth Australia's annual Level 3 land cover classification for 2010 or 2025 when its source is set to **DEA Land Cover** (the default). The layer is drawn straight from DEA's public map service, and switching years never moves the map. The code is in [`src/map/deaLandCover.ts`](../src/map/deaLandCover.ts), [`src/map/analysisLayers.ts`](../src/map/analysisLayers.ts), [`src/components/AnalysisLayerPanel.tsx`](../src/components/AnalysisLayerPanel.tsx) and [`src/components/GoldCoastMap.tsx`](../src/components/GoldCoastMap.tsx). The same panel also offers this project's Sentinel-2 outputs, described in [spectral-indices.md](spectral-indices.md); only one analysis raster is shown at a time.

All facts below were checked on 4 November 2026.

## Product

| Item | Value |
| --- | --- |
| Product | DEA Land Cover (Landsat), technical name "Geoscience Australia Landsat Land Cover 30m" |
| Product ID | `ga_ls_landcover_class_cyear_3` (Collection 3) |
| Version | 2.0.0 for both years used here (from each dataset's `odc:dataset_version`) |
| Classification shown | Level 3 (the `level3` band) |
| Resolution | 30 m, stored in Australian Albers (EPSG:3577) |
| Years available | 1988 to 2025. The 2025 update was released on 30 April 2026 |
| Year convention | Each year summarises Landsat observations from 1 January to 31 December. The 2010 datasets cover `2010-01-01 00:00:00Z` to `2010-12-31 23:59:59.999999Z`, and the 2025 datasets cover the same span in 2025 |
| Licence | Creative Commons Attribution 4.0 International (CC BY 4.0) |
| Copyright | © Commonwealth of Australia (Geoscience Australia) |
| Product page | https://knowledge.dea.ga.gov.au/data/product/dea-land-cover-landsat/ |
| Data citation | DEA Land Cover 30m. Geoscience Australia, Canberra. https://doi.org/10.26186/149976 |

## Map service

The app uses DEA's OGC Web Map Tile Service (WMTS). The product page lists it under "OGC web services" as https://ows.dea.ga.gov.au/.

| Item | Value | Where it comes from |
| --- | --- | --- |
| Endpoint | `https://ows.dea.ga.gov.au/wmts` (KVP `GetTile`, version 1.0.0) | WMTS GetCapabilities |
| Layer | `ga_ls_landcover_c3`, "DEA Land Cover Collection 3 Calendar Year (Landsat)" | WMTS and WMS GetCapabilities |
| Style | `level3`, "Basic: Standardised colouring of Level 3 land cover classes". The service's default style is `level4`, so the app always names the style | WMTS GetCapabilities |
| Tile matrix set | `WholeWorld_WebMercator`: EPSG:3857, GoogleMapsCompatible, 256 × 256 px, top-left origin. It uses the same `z/x/y` numbering as MapLibre | WMTS GetCapabilities |
| Time dimension | `1988-01-01` … `2025-01-01`, one value per year; default `2025-01-01` | WMTS and WMS GetCapabilities |
| Format | `image/png` (RGBA) | WMTS GetCapabilities |
| Browser access | `Access-Control-Allow-Origin: *` on capabilities and tiles | Response headers |
| Caching | `Cache-Control: max-age=3600`, served through CloudFront | Response headers |
| API key | None | |
| Service status | https://status.dea.ga.gov.au | Layer abstract |

The capabilities also list an older layer, `ga_ls_landcover`, whose time dimension stops at 2020-01-01. That is the previous Collection 2 (version 1.0.0) product, and the app does not use it. DEA's own DEA Maps catalogue (the `prod/terria/dea-maps-v8.json` file in the GeoscienceAustralia/dea-config repository) points its "DEA Land Cover C3 (Landsat)" item at the same `https://ows.dea.ga.gov.au/` service and `ga_ls_landcover_c3` layer.

### Tile URLs

The app builds one tile template per year. `{z}`, `{x}` and `{y}` are filled in by MapLibre:

```
https://ows.dea.ga.gov.au/wmts?service=WMTS&request=GetTile&version=1.0.0&layer=ga_ls_landcover_c3&style=level3&format=image%2Fpng&tileMatrixSet=WholeWorld_WebMercator&Time=2010-01-01&tileMatrix={z}&tileCol={x}&tileRow={y}
https://ows.dea.ga.gov.au/wmts?service=WMTS&request=GetTile&version=1.0.0&layer=ga_ls_landcover_c3&style=level3&format=image%2Fpng&tileMatrixSet=WholeWorld_WebMercator&Time=2025-01-01&tileMatrix={z}&tileCol={x}&tileRow={y}
```

### Year parameter

The year is sent as the WMTS `Time` dimension, using the exact value listed in the capabilities: `2010-01-01` or `2025-01-01`. The service validates it strictly:

| `Time` sent | Response |
| --- | --- |
| `2010-01-01` (also as `time` or `TIME`) | 200, 2010 tile |
| `2025-01-01` | 200, 2025 tile |
| omitted | 200, identical to the 2025 tile (the default) |
| `2026-01-01`, `2010`, `2010-06-30` | 400 `InvalidDimensionValue` |

The service only accepts listed dates, so it is reading the parameter, not ignoring it.

## How the year selection was verified

Visual differences between the two years were not taken as proof. These checks were made against the service and the source data:

1. **Capabilities.** `ga_ls_landcover_c3` lists both `2010-01-01` and `2025-01-01` in WMS and WMTS.
2. **Feature info.** A WMS `GetFeatureInfo` at Surfers Paradise (`time=2010-01-01` and `time=2025-01-01`) returned `"time": "2010-01-01"` and `"time": "2025-01-01"`. The data links were `…/ga_ls_landcover_class_cyear_3/2-0-0/x67/y38/2010--P1Y` and `…/2-0-0/x67/y38/2025--P1Y`.
3. **Dataset metadata.** The `odc-metadata.yaml` for tile `x67y38` in both years reports `odc:product: ga_ls_landcover_class_cyear_3` and `odc:dataset_version: 2.0.0`, with the calendar-year date ranges above.
4. **Tile pixels against the source rasters.** At zoom 13, WMTS tiles for both years were fetched at eight places. Each tile pixel's colour was decoded to its class and compared with DEA's continental Level 3 GeoTIFF mosaic for the same year, at the same ground position. The mosaics are `continental_mosaics/2010--P1Y/…_level3.tif` and `…/2025--P1Y/…_level3.tif`, read in EPSG:3577. Only pixels whose 3 × 3 source neighbourhood is a single class were counted.

   | Place | Comparable pixels | Changed 2010→2025 | Most common change |
   | --- | --- | --- | --- |
   | Pimpama | 22,087 | 4,710 | (Semi-)Natural Terrestrial Vegetation → Artificial Surface |
   | Coomera | 22,718 | 1,062 | (Semi-)Natural Terrestrial Vegetation → Artificial Surface |
   | Jacobs Well | 24,871 | 2,579 | (Semi-)Natural → Cultivated Terrestrial Vegetation |
   | Surfers Paradise | 38,051 | 49 | (Semi-)Natural Terrestrial Vegetation → Artificial Surface |
   | Hinze Dam | 51,652 | 735 | (Semi-)Natural Terrestrial Vegetation → Water |
   | Reedy Creek | 17,678 | 718 | (Semi-)Natural → Cultivated Terrestrial Vegetation |
   | Springbrook | 53,943 | 242 | (Semi-)Natural → Cultivated Terrestrial Vegetation |
   | Coolangatta | 30,296 | 258 | (Semi-)Natural Terrestrial Vegetation → Artificial Surface |

   Across all 261,296 comparable pixels, each year's tiles matched that year's source on 100% of pixels. On the 10,353 pixels whose class changed, the 2010 tiles matched the 2010 source 100% of the time and the 2025 source 0% of the time, and vice versa.
5. **Digital Atlas of Australia.** DEA's product page links to a second official service, the Level 3 ImageServer at `https://di-daa.img.arcgis.com/arcgis/rest/services/Land_and_vegetation/DEA_Landcover_Landsat_Level3/ImageServer`. Its `identify` operation was called at one changed pixel per place, with `time` set to 1 January of each year. All 16 values matched the source rasters. The matching catalogue items are named `ga_ls_landcover_class_cyear_3_x67y38_2010-01-01_final` / `…_2025-01-01_final` and `Landcover_Level3_…_2010_ver_2_0_0` / `…_2025_ver_2_0_0`.
6. **In the app.** At each changed pixel, the colour drawn on screen for each year was that year's source class. This was checked at zoom 14 and 100% opacity, with the basemap hidden.

DEA Maps itself was not opened interactively. It was checked only through its published catalogue configuration, as described under *Map service*.

## Classes and colours

The colours are DEA's official Level 3 palette from the QGIS style file `https://dea-public-data.s3.ap-southeast-2.amazonaws.com/derivative/ga_ls_landcover_class_cyear_3/ga_ls_landcover_class_cyear_3_style.qml`. Every tile fetched contained only these six opaque colours plus fully transparent pixels.

| Value | Name in the app (product documentation) | Name in the service legend | Colour |
| --- | --- | --- | --- |
| 111 | Cultivated Terrestrial Vegetation | Cultivated Terrestrial Vegetation | `#acbc2d` |
| 112 | (Semi-)Natural Terrestrial Vegetation | Natural Terrestrial Vegetation | `#0e7912` |
| 124 | Natural Aquatic Vegetation | Natural Aquatic Vegetation | `#1ebf79` |
| 215 | Artificial Surface | Artificial Surface | `#da5c69` |
| 216 | Natural Bare Surface | Natural Bare Surface | `#f3ab69` |
| 220 | Water | Water | `#4d9fdc` |
| 255 | No data | (not drawn) | transparent |

The app uses the class names from the product documentation's Level 3 table, without their abbreviations (CTV, NTV and so on). The service's own legend image and feature info shorten class 112 to "Natural Terrestrial Vegetation".

## Processing

This project does no preprocessing and stores no land cover files. Nothing is downloaded or generated at build time.

- **Clipping:** none. The layer is not clipped to the Gold Coast boundary (see *Displayed extent*).
- **Reprojection:** done by DEA's service, not by this project. The source is 30 m EPSG:3577 and the service returns EPSG:3857 tiles. The app draws them as they come, with no further reprojection.
- **Resampling:**
  - **On the server.** DEA's service resamples to each tile's grid. Its output contains only class colours, with no blends, and matched the source class at every pixel compared above.
  - **In the browser.** With **Smooth display** on (the default), MapLibre enlarges tiles with linear sampling, which blends neighbouring class colours on screen. With it off, MapLibre uses nearest-neighbour sampling, so no blended colours are added. Beyond zoom 14, it enlarges the zoom-14 tiles.
- **Colour:** the service applies the official palette. The app's opacity setting then blends the whole layer evenly with the map beneath. This is a display setting and does not change classes.

### Smooth display and exact class colours

The panel's **Smooth display** switch chooses how tile pixels are drawn. It changes rendering only; the tiles and their classes are the same either way.

- **On (default): `raster-resampling: linear`.** Enlarged pixels blend into their neighbours, so 30 m cells look soft instead of blocky. A blend between two class colours can look like a third class, and the panel says so under the switch.
- **Off: `raster-resampling: nearest`.** Every pixel on screen is an exact class colour, as in Milestone 3.

Three further settings keep the "off" state exact. They are the same in both states, so switching never reloads tiles:

- **Floor zoom (`roundZoom = false`).**
  - **The problem.** By default MapLibre rounds the zoom when choosing raster tiles. At zoom 12.6 it would use zoom-13 tiles drawn at 76% of their size. The GPU shrinks textures with linear filtering, which blends neighbouring classes. This is not affected by `raster-resampling`.
  - **The fix.** The app sets the public `roundZoom` property of each analysis source to `false`, so MapLibre uses the lower zoom level. Tiles are then always drawn at 100–200% of their size, so only enlargement applies.
  - **Measured (Milestone 3).** At zooms 9.4, 9.6, 11.3, 11.7, 12.6 and 13.5, all of about 1.15 million land cover pixels on screen were exact palette colours. With MapLibre's default rounding at zoom 12.6, 129,658 pixels were blended colours.
  - **The cost.** Between whole zoom levels, the layer uses tiles up to one level coarser than MapLibre would otherwise choose. From zoom 13 upwards, tile pixels (17 m or smaller) are still finer than the 30 m data.
- **No anisotropic filtering (`anisotropicFilterPitch: 180`).** MapLibre normally turns on anisotropic filtering for raster tiles whenever the map is tilted more than 20°, and never turns it off for tiles already loaded. On both SwiftShader and an Intel GPU (Direct3D 11), those tiles then stayed blended with Smooth display off, even after the map returned to top-down (68,936 blended pixels in a 500 × 300 px view of the Sentinel-2 classes at Arundel). The map option is set to its maximum, 180°, which no pitch reaches, and the same view then had 0 blended pixels.
- **`raster-fade-duration: 0`** stops MapLibre cross-fading a tile with its parent, which would briefly blend two classes.

**Measured (this milestone)** at Arundel, 100% opacity, basemap hidden, after the map had been tilted to 30° and back:
- **Off:** at zooms 12.6, 13.5 and 15.2, every pixel was an exact class colour.
- **On:** blended colours made up 24.3%, 9.7% and 7.2% of the pixels at those zooms.

**Tile edges.** MapLibre samples each tile on its own, so linear blending stops at tile edges. Where tiles are enlarged a lot (about zoom 16 and beyond, where zoom-14 tiles are drawn at 4× or more), this leaves faint straight lines every 256 tile pixels (about 2.2 km). Switching Smooth display off removes them.

### Zoom range

| Setting | Value | Reason |
| --- | --- | --- |
| `minzoom` | 7 | At zoom 5–6 the service returns a translucent blue coverage placeholder (`rgba(44,104,144,0.25)`) instead of classes. Tested at Darwin, Hobart and the Gold Coast. Zoom 7 returns real classes at all three. Below zoom 7 the panel says "Zoom in to see this layer." |
| `maxzoom` | 14 | About 8.4 m per tile pixel at this latitude, so each 30 m cell spans about 3.6 tile pixels. Deeper zooms enlarge zoom-14 tiles instead of requesting tiles that only repeat the same 30 m cells. |
| `bounds` | 112.343°E to 155.074°E, 44.340°S to 9.404°S | The layer's WGS84 bounding box from the capabilities. No tiles are requested outside it. |

## Displayed extent

DEA's layer covers all of Australia, so the colours do not stop at the Gold Coast boundary. They continue:

- inland into neighbouring council areas and New South Wales
- offshore, where the 2025 data runs about 75 km east of the coast at 27.8°S and about 130 km east at 28.17°S. Samples between 153.6°E and 154.0°E along three latitudes were all Water. At 27.8°S, the outermost data pixel is classed as Cultivated Terrestrial Vegetation.

DEA's product page says "Classification of pixels over the ocean should not be used from Land Cover" and recommends an ocean mask for coastal tiles. The panel's *Legend and source* section repeats this, and the purple outline shows the study area.

## How it works in the app

### From a year click to pixels on the map

1. **The click.** Pressing **2010** in the Year group calls `selectDeaYear(2010)` in `GoldCoastMap`. That calls `applyAnalysisSelection`, which:
   - stores the selection in React state and records the active layer key `dea-2010` in `activeAnalysisLayerRef`
   - sets the load status to `loading`
   - calls `showAnalysisLayer(map, deaLayerDefinition(2010), opacity, isDisplaySmoothed)`
2. **Sources and layers.** `showAnalysisLayer` hides every other analysis layer (the other DEA year and any Sentinel-2 view). The first time 2010 is chosen, it adds:
   - a raster source `analysis-dea-2010`, whose tile template has `Time=2010-01-01`
   - a raster layer `analysis-dea-2010-layer`, placed directly below the Gold Coast outline

   It then makes the 2010 layer visible. The camera is never touched, so position, zoom, rotation and tilt stay as they were.
3. **Tile requests.** On the next frame, MapLibre works out which `z/x/y` tiles cover the view, using floor zoom between 7 and 14, and fills in the template. The browser requests each tile from `ows.dea.ga.gov.au`. DEA's service selects the 2010 dataset, reprojects and resamples it to the tile, colours it with the `level3` palette and returns a PNG.
4. **Drawing.** MapLibre's web worker decodes each PNG, and the image becomes a texture on the graphics card. The raster layer draws it at the chosen opacity, with linear sampling when Smooth display is on or nearest-neighbour sampling when it is off. It sits above roads and buildings, and below the Gold Coast outline and all labels.
5. **Status.**
   - While tiles for the selected year are loading, `sourcedataloading` events keep the panel at "Loading DEA land cover 2010…".
   - When the map next becomes `idle` with that source fully loaded, the message clears.
   - The caption under the slider always names the selected year, with "DEA Level 3 · 30 m pixels".

### Reuse

Each year (and each Sentinel-2 view) has one source and one layer, created the first time it is shown and then kept. Switching only changes `visibility`. Switching back re-uses the source, and recent tiles come from MapLibre's tile cache or the browser's HTTP cache. Opacity changes update `raster-opacity` on every analysis layer, so all of them always match the slider. In the same way, Smooth display updates `raster-resampling` on every analysis layer, and layers created later start with the current setting.

### Slow responses for an earlier selection

The two years never share a source or layer. A 2010 tile can only ever be drawn by the 2010 layer, and that layer is hidden as soon as another year is selected. A late 2010 response therefore cannot appear while 2025 is selected.

Status events are also filtered. Loading, ready and error events only change the panel when they come from the selected layer's source.

This was tested by holding back every 2010 tile response, switching 2010 → 2025, then releasing the held tiles as solid magenta images:
- **2025 selected:** no magenta pixel appeared, and the status showed 2025 as ready.
- **2010 selected again:** the same magenta tiles did appear.
- **Rapid clicks:** six quick alternating clicks ending on 2025 also gave no magenta.

### Failures

MapLibre reports a failed tile request (network failure, HTTP 5xx) as an `error` event carrying the source id.

- **For the selected year:** the panel shows "Some DEA land cover 2010 tiles could not be loaded. The rest of the map still works." as an alert, with a **Try again** button. Any tiles that did load stay visible.
- **For a year that is not selected:** nothing is shown.
- **Recovery:** in both cases the year is marked as failed. The next time it is shown, or when **Try again** is pressed, its source and layer are removed and added again, so every tile is requested afresh.

### Show, hide and attribution

**Show** hides or shows the selected layer, and the source, year, opacity and Smooth display controls are disabled while it is hidden. MapLibre lists a source's attribution only while one of its layers is visible. The line "Land cover: DEA Land Cover v2.0.0 © Commonwealth of Australia (Geoscience Australia), CC BY 4.0" is therefore at the bottom right whenever land cover is shown, with links to the product page and the licence. The panel's *Legend and source* section credits the classification to Digital Earth Australia, with the product, level, version, copyright and licence.

### Layer order

From bottom to top:

1. basemap land fills
2. terrain hillshade, when on
3. water
4. roads and buildings
5. land cover
6. Gold Coast outline
7. basemap boundaries and labels

The land cover is inserted directly below `gold-coast-boundary-outline`, falling back to the first label layer.

## Basemap, terrain shading and land cover

| | Basemap | Terrain shading | Land cover |
| --- | --- | --- | --- |
| What it shows | Streets, places, water and land use from OpenStreetMap | Light and shadow on slopes, from elevation | DEA's classification of each 30 m cell for one calendar year |
| Data type | Vector tiles, styled in the browser | Elevation tiles (`raster-dem`, heights encoded in RGB) | Pre-coloured categorical PNG tiles (`raster`) |
| Provider | OpenFreeMap | Mapterhorn | Digital Earth Australia (Geoscience Australia) |
| Time | Current OpenStreetMap | Static | 2010 or 2025, chosen by the `Time` parameter |
| Drawn by | Many style layers | One `hillshade` layer computing slopes on the GPU | One `raster` layer per year, drawing the tile colours as they are |
| Default | Always on | Off | On, 2025, 70% opacity, smooth display |

At 70% opacity, the basemap's roads and the terrain relief stay faintly visible through the land cover. Lowering the opacity shows more of both.

## Limitations

- **Over the sea and outside the study area.** The layer is not clipped (see *Displayed extent*).
- **Phone screens.** On a 375 px wide screen, the collapsed panel (about 280 px tall) covers part of the northern Gold Coast at the startup view. The startup framing was left unchanged.
- **Tilted views.** In tilted views (right-drag or two-finger tilt), distant tiles are drawn smaller than their size. The GPU's minification filter can then blend class colours near the horizon, even with Smooth display off. The same can happen if the browser is zoomed out below 100%. Top-down views at normal browser zoom are unaffected, including after the map has been tilted and returned. With anisotropic filtering off, distant tiles in tilted views also look slightly softer than MapLibre's default would draw them.
- **Below zoom 7** no land cover is drawn, because the service only returns a coverage placeholder there.
- **Partial failures.** If a tile fails, the tiles that did load stay visible and the message shows. Until **Try again** is pressed, gaps from failed tiles could be mistaken for no data.
- **Service terms.** DEA publishes no rate limits for the public service. Tiles are requested directly by each visitor's browser from DEA's servers (via CloudFront), and only while land cover is shown.

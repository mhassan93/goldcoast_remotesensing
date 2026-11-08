# Land cover

The **Analysis layer** panel shows Digital Earth Australia's annual Level 3 land cover classification for 2010, 2015, 2020 or 2025 when its source is set to **DEA Land Cover** (the default). The layer is clipped to the City of Gold Coast boundary, so the street map shows through everywhere outside it. Switching years never moves the map.

- **Tiles:** this project cuts them from DEA's published Level 3 GeoTIFFs with the `dea-tiles` stage of the Python pipeline in [`analysis/spectral_indices/dea_land_cover.py`](../analysis/spectral_indices/dea_land_cover.py). They are served as static files from [`public/data/dea-land-cover/`](../public/data/dea-land-cover).
- **App code:** [`src/map/deaLandCover.ts`](../src/map/deaLandCover.ts), [`src/map/analysisLayers.ts`](../src/map/analysisLayers.ts), [`src/components/AnalysisLayerPanel.tsx`](../src/components/AnalysisLayerPanel.tsx) and [`src/components/GoldCoastMap.tsx`](../src/components/GoldCoastMap.tsx).
- **Sentinel-2:** the same panel also offers this project's Sentinel-2 outputs, described in [spectral-indices.md](spectral-indices.md). Only one analysis raster is shown at a time.

Facts below were checked on 4 November 2026, and the clipping on 8 November 2026.

## Product

| Item | Value |
| --- | --- |
| Product | DEA Land Cover (Landsat), technical name "Geoscience Australia Landsat Land Cover 30m" |
| Product ID | `ga_ls_landcover_class_cyear_3` (Collection 3) |
| Version | 2.0.0 for all four years used here (the `2-0-0` folder of each mosaic) |
| Classification shown | Level 3 |
| Resolution | 30 m, stored in Australian Albers (EPSG:3577) |
| Years available | 1988 to 2025. The 2025 update was released on 30 April 2026 |
| Years shown | 2010, 2015, 2020 and 2025 |
| Year convention | Each year summarises Landsat observations from 1 January to 31 December |
| Licence | Creative Commons Attribution 4.0 International (CC BY 4.0) |
| Copyright | © Commonwealth of Australia (Geoscience Australia) |
| Product page | https://knowledge.dea.ga.gov.au/data/product/dea-land-cover-landsat/ |
| Data citation | DEA Land Cover 30m. Geoscience Australia, Canberra. https://doi.org/10.26186/149976 |

## Source rasters

The tiles come from DEA's continental Level 3 mosaics, one cloud-optimised GeoTIFF per year. The URL template is `dea_level3_mosaic` in [`analysis/config.toml`](../analysis/config.toml):

```
https://dea-public-data.s3.ap-southeast-2.amazonaws.com/derivative/ga_ls_landcover_class_cyear_3/2-0-0/continental_mosaics/{year}--P1Y/ga_ls_landcover_class_cyear_3_mosaic_{year}--P1Y_level3.tif
```

| Item | Value |
| --- | --- |
| Access | Anonymous HTTPS from DEA's public S3 bucket. No account, key or payment |
| Format | uint8, no-data 255, internal 1024 × 1024 blocks, zstd compression, overviews at 2×, 4× and 8× |
| Size | 756–873 MB per year for the whole of Australia |
| Read for this project | Only a window around the boundary: 1,291 × 2,216 pixels (the boundary's bounding box plus 1.5 km), 0.37–0.59 MB of compressed blocks per year, in under 2 s each |
| Cache | `analysis/work/dea_land_cover/level3_{year}.tif`, which Git ignores |

The `dea-tiles` stage checks each mosaic's CRS, resolution, data type and no-data value before reading. It stops if a pixel holds any value other than the six Level 3 classes and 255.

**Earlier versions of the app** drew this layer from DEA's public WMTS service (`https://ows.dea.ga.gov.au/wmts`, layer `ga_ls_landcover_c3`, style `level3`), which cannot clip to a polygon. That version's checks found that the WMTS tiles matched these same mosaics on every comparable pixel. The browser no longer contacts the service, and the production Content Security Policy no longer allows it.

## Clipping and tiling

`python -m spectral_indices dea-tiles` writes zoom 7–14 tiles for every configured year. The settings are in `[dea_land_cover]` in `config.toml`.

1. **Boundary in each coordinate system.**
   - **For the source mosaics:** the official GDA2020 boundary is transformed to EPSG:3577 with pyproj ("Inverse of GDA94 to GDA2020 (1) + Australian Albers").
   - **For the tile grid:** the same coordinates are projected straight to Web Mercator, which is how MapLibre draws the purple outline. The clipped edge therefore lines up with the outline on screen.
2. **Reprojection to each zoom's tile grid** (EPSG:3857, 256 px tiles), reusing the Sentinel-2 export code:
   - **Zooms 13 and 14** (16.9 and 8.4 m per tile pixel): nearest neighbour. Each tile pixel takes the class of the 30 m cell under its centre.
   - **Zooms 7–12** (33.8 m to 1.1 km per tile pixel): mode, the most common class. Only source cells whose centres lie inside the boundary take part, so ocean or neighbouring land outside the boundary never decides a coastal pixel's class.
3. **The boundary mask on every zoom.** On each zoom's own tile grid, a tile pixel is kept only if its centre lies inside the boundary, and every other pixel is made transparent. This is what keeps the lower zooms clipped too. Large tile pixels that straddle the boundary would otherwise spill over it, and cropping to the boundary's bounding rectangle would leave the sea and neighbouring council areas visible.
4. **Classes and colours.** Each opaque pixel's palette index is its official Level 3 class code (111, 112, 124, 215, 216 or 220), coloured with DEA's palette (below). DEA's no-data value 255 and everything outside the boundary become palette index 0, which is fully transparent.
5. **Coverage.** Every tile in the boundary's bounding box is written, including fully transparent ones, so the browser never requests a missing tile.

| Output | Value |
| --- | --- |
| Tiles | 789 per year (from 1 at zoom 7 to 570 at zoom 14), 3,156 in total |
| Size | 1.60 MB (2010), 1.74 MB (2015), 1.69 MB (2020), 2.05 MB (2025); 7.08 MB with `layers.json` |
| Largest tile | 12 KB |
| Records | [`analysis/results/dea_land_cover/processing_manifest.json`](../analysis/results/dea_land_cover/processing_manifest.json) lists the windows, bytes read, transformation, resampling per zoom, tile counts and sizes |

**DEA no-data inside the boundary.** DEA itself has no class for 0.45 km² (2010), 1.09 km² (2015), 1.58 km² (2020) and 1.69 km² (2025) inside the boundary, as scattered pixels mostly in the western hinterland. They stay transparent, as in DEA's own products.

## Verification

`python -m spectral_indices dea-verify` re-reads every tile and writes [`analysis/results/dea_land_cover/verification.json`](../analysis/results/dea_land_cover/verification.json). It does not reuse the export's masks. All checks passed for all four years:

- **Nothing outside the boundary.** At every zoom from 7 to 14, no opaque pixel lies outside the boundary, even counting every pixel the boundary line merely touches. That covers about 25.9 million opaque pixels per year.
- **Pixel-centre rule.** At each zoom, 20,000 random tile pixels were tested with a separate point-in-polygon test (ray casting on the boundary's 5,646 vertices).
  - **Outside the boundary:** no pixel was opaque.
  - **Inside the boundary:** the 0–16 transparent pixels per zoom were all DEA no-data at the pixel centre.
- **Coast and edges.** Twelve named points were checked at every zoom, and the tile always matched the boundary:
  - **Transparent:** the ocean off Surfers Paradise, Main Beach, Burleigh Heads and Coolangatta; the beach sand east of the Surfers Paradise esplanade, which is outside the LGA polygon; and the Tweed River in New South Wales.
  - **Coloured:** the Broadwater, the Seaway, South Stradbroke Island, southern Moreton Bay, Hinze Dam and the Logan River edge.
  - **Large pixels:** at zooms 7 and 9, where one tile pixel spans hundreds of metres, a beach point can fall in a coloured pixel whose centre is inland. This is consistent with the pixel-centre rule.
- **Interior classes against the original data.** At zooms 13 and 14, every opaque pixel (4.85 and 19.4 million per year) was compared with the source class at its centre. The pixel centres were transformed independently with pyproj.
  - **Uniform 3 × 3 neighbourhoods:** 100% match. These are pixels whose source cell and its eight neighbours share one class, 61–76% of pixels depending on year and zoom.
  - **Overall:** 99.62–99.80% match. Every remaining pixel lies at a class edge and takes the class of an adjacent source cell. This is a sub-pixel difference between the transformation pyproj chooses here and the one GDAL used for tiling.
- **Source copy.** 500 random cells of each year's cached window matched the remote mosaic read directly.
- **Palette.** Every tile is 8-bit paletted with index 0 transparent, and every index used carries its official colour. Only the six class codes occur.

## Classes and colours

The colours are DEA's official Level 3 palette from the QGIS style file `https://dea-public-data.s3.ap-southeast-2.amazonaws.com/derivative/ga_ls_landcover_class_cyear_3/ga_ls_landcover_class_cyear_3_style.qml`. They are set in `[dea_land_cover]` in `config.toml` for the tiles and in `deaLandCover.ts` for the legend.

| Value | Name in the app (product documentation) | Name in DEA's map service legend | Colour |
| --- | --- | --- | --- |
| 111 | Cultivated Terrestrial Vegetation | Cultivated Terrestrial Vegetation | `#acbc2d` |
| 112 | (Semi-)Natural Terrestrial Vegetation | Natural Terrestrial Vegetation | `#0e7912` |
| 124 | Natural Aquatic Vegetation | Natural Aquatic Vegetation | `#1ebf79` |
| 215 | Artificial Surface | Artificial Surface | `#da5c69` |
| 216 | Natural Bare Surface | Natural Bare Surface | `#f3ab69` |
| 220 | Water | Water | `#4d9fdc` |
| 255 | No data | (not drawn) | transparent |

The app uses the class names from the product documentation's Level 3 table, without their abbreviations (CTV, NTV and so on).

## Processing summary

- **Clipping:** to the City of Gold Coast boundary at every zoom, as described above.
- **Reprojection and resampling:** done by this project from EPSG:3577 to EPSG:3857 tiles: nearest neighbour at zooms 13–14 and mode at zooms 7–12. Beyond zoom 14, MapLibre enlarges the zoom-14 tiles.
- **Classes:** unchanged. The class codes and colours are DEA's own.
- **In the browser:** with **Smooth display** on (the default), MapLibre enlarges tiles with linear sampling, which blends neighbouring class colours on screen. With it off, it uses nearest-neighbour sampling, so no blended colours are added.
- **Opacity:** blends the whole layer evenly with the map beneath. This is a display setting and does not change classes.

### Smooth display and exact class colours

The panel's **Smooth display** switch chooses how DEA tile pixels are drawn. It changes rendering only; the tiles and their classes are the same either way. It appears only while the source is DEA Land Cover. The Sentinel-2 views have fixed rendering instead (see [spectral-indices.md](spectral-indices.md#web-outputs)), and the switch never affects them.

- **On (default): `raster-resampling: linear`.** Enlarged pixels blend into their neighbours, so 30 m cells look soft instead of blocky. A blend between two class colours can look like a third class, and the panel says so under the switch.
- **Off: `raster-resampling: nearest`.** Every pixel on screen is an exact class colour.

Three further settings keep the "off" state exact. They are the same in both states, so switching never reloads tiles:

- **Floor zoom (`roundZoom = false`).**
  - **The problem.** By default MapLibre rounds the zoom when choosing raster tiles. At zoom 12.6 it would use zoom-13 tiles drawn at 76% of their size. The GPU shrinks textures with linear filtering, which blends neighbouring classes. This is not affected by `raster-resampling`.
  - **The fix.** The app sets the public `roundZoom` property of each analysis source to `false`, so MapLibre uses the lower zoom level. Tiles are then always drawn at 100–200% of their size, so only enlargement applies.
  - **Measured (with the earlier WMTS tiles).** At zooms 9.4, 9.6, 11.3, 11.7, 12.6 and 13.5, all of about 1.15 million land cover pixels on screen were exact palette colours. With MapLibre's default rounding at zoom 12.6, 129,658 pixels were blended colours.
  - **The cost.** Between whole zoom levels, the layer uses tiles up to one level coarser than MapLibre would otherwise choose. From zoom 13 upwards, tile pixels (17 m or smaller) are still finer than the 30 m data.
- **No anisotropic filtering (`anisotropicFilterPitch: 180`).** MapLibre normally turns on anisotropic filtering for raster tiles whenever the map is tilted more than 20°, and never turns it off for tiles already loaded. On both SwiftShader and an Intel GPU (Direct3D 11), those tiles then stayed blended with Smooth display off, even after the map returned to top-down (68,936 blended pixels in a 500 × 300 px view at Arundel). The map option is set to its maximum, 180°, which no pitch reaches, and the same view then had 0 blended pixels.
- **`raster-fade-duration: 0`** stops MapLibre cross-fading a tile with its parent, which would briefly blend two classes.

**Tile edges.** MapLibre samples each tile on its own, so linear blending stops at tile edges. Where tiles are enlarged a lot (about zoom 16 and beyond, where zoom-14 tiles are drawn at 4× or more), this leaves faint straight lines every 256 tile pixels (about 2.2 km). Switching Smooth display off removes them.

### Zoom range

| Setting | Value | Reason |
| --- | --- | --- |
| `minzoom` | 7 | Matches the earlier app. At zoom 7 the whole City of Gold Coast is about 40 × 60 px. Below zoom 7 the panel says "Zoom in to see this layer." |
| `maxzoom` | 14 | About 8.4 m per tile pixel at this latitude, so each 30 m cell spans about 3.6 tile pixels. Deeper zooms enlarge zoom-14 tiles instead of requesting tiles that only repeat the same 30 m cells. Zoom 13 alone (16.9 m) would draw 30 m cells alternately 1 and 2 tile pixels wide. |
| `bounds` | 153.169°E to 153.552°E, 28.265°S to 27.690°S | The boundary's bounding box, the same as the Sentinel-2 layers. No tiles are requested outside it. |

## Displayed extent

The layer stops at the City of Gold Coast boundary at every zoom. The sea, the New South Wales side of the border and neighbouring council areas show the street map only.

- **Inside:** South Stradbroke Island, the Broadwater and the southern part of Moreton Bay that belongs to the city.
- **Outside:** most mainland ocean beaches, because the LGA boundary follows the esplanade there (for example at Surfers Paradise, Main Beach, Burleigh and Palm Beach). The Sentinel-2 layers stop at the same line.
- **Ocean classes:** DEA's product page says "Classification of pixels over the ocean should not be used from Land Cover". Clipping removes the open ocean that the unclipped layer used to show as Water.

## How it works in the app

### From a year click to pixels on the map

1. **The click.** Pressing **2015** in the Year group calls `selectDeaYear(2015)` in `GoldCoastMap`. That calls `applyAnalysisSelection`, which:
   - stores the selection in React state and records the active layer key `dea-2015` in `activeAnalysisLayerRef`
   - sets the load status to `loading`
   - calls `showAnalysisLayer(map, deaLayerDefinition(2015), opacity, isDisplaySmoothed)`
2. **Sources and layers.** `showAnalysisLayer` hides every other analysis layer (the other DEA years and any Sentinel-2 view). The first time 2015 is chosen, it adds:
   - a raster source `analysis-dea-2015`, whose tile template is `…/data/dea-land-cover/2015/{z}/{x}/{y}.png` under the site's base path
   - a raster layer `analysis-dea-2015-layer`, placed directly below the Gold Coast outline

   It then makes the 2015 layer visible. The camera is never touched, so position, zoom, rotation, tilt and opacity stay as they were.
3. **Tile requests.** On the next frame, MapLibre works out which `z/x/y` tiles cover the view, using floor zoom between 7 and 14, and requests them from the same site as the app.
4. **Drawing.** MapLibre's web worker decodes each PNG, and the image becomes a texture on the graphics card. The raster layer draws it at the chosen opacity, with linear sampling when Smooth display is on or nearest-neighbour sampling when it is off. It sits above roads and buildings, and below the Gold Coast outline and all labels.
5. **Status.**
   - While tiles for the selected year are loading, `sourcedataloading` events keep the panel at "Loading DEA land cover 2015…".
   - When the map next becomes `idle` with that source fully loaded, the message clears.
   - The caption under the slider always names the selected year, with "DEA Level 3 · 30 m pixels".

### Reuse

Each year (and each Sentinel-2 year and view) has one source and one layer, created the first time it is shown and then kept. Switching only changes `visibility`. Switching back re-uses the source, and recent tiles come from MapLibre's tile cache or the browser's HTTP cache. Opacity changes update `raster-opacity` on every analysis layer, so all of them always match the slider. Smooth display updates `raster-resampling` on the DEA layers only, and DEA layers created later start with the current setting.

### Slow responses for an earlier selection

The years never share a source or layer. A 2010 tile can only ever be drawn by the 2010 layer, and that layer is hidden as soon as another year is selected. A late 2010 response therefore cannot appear while another year is selected. Status events are also filtered: loading, ready and error events only change the panel when they come from the selected layer's source. The same design covers the Sentinel-2 years, where it was tested with held responses (see [spectral-indices.md](spectral-indices.md#years)).

### Failures

MapLibre reports a failed tile request (network failure, HTTP 5xx) as an `error` event carrying the source id.

- **For the selected year:** the panel shows "Some DEA land cover 2010 tiles could not be loaded. The rest of the map still works." as an alert, with a **Try again** button. Any tiles that did load stay visible.
- **For a year that is not selected:** nothing is shown.
- **Recovery:** in both cases the year is marked as failed. The next time it is shown, or when **Try again** is pressed, its source and layer are removed and added again, so every tile is requested afresh.

### Show, hide and attribution

**Show** hides or shows the selected layer, and the source, year, opacity and Smooth display controls are disabled while it is hidden. MapLibre lists a source's attribution only while one of its layers is visible. The line "Land cover: DEA Land Cover v2.0.0 © Commonwealth of Australia (Geoscience Australia), CC BY 4.0, clipped to the study area" is therefore at the bottom right whenever land cover is shown, with links to the product page and the licence. The panel's *Legend and source* section credits the classification to Digital Earth Australia, with the product, level, version, copyright and licence. It also says that this project clipped the data and left the class codes and colours unchanged, as CC BY 4.0 asks when material is modified.

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
| Provider | OpenFreeMap | Mapterhorn | Digital Earth Australia (Geoscience Australia), clipped and tiled by this project |
| Served from | OpenFreeMap | Mapterhorn | This site (`public/data/dea-land-cover/`) |
| Time | Current OpenStreetMap | Static | 2010, 2015, 2020 or 2025 |
| Drawn by | Many style layers | One `hillshade` layer computing slopes on the GPU | One `raster` layer per year, drawing the tile colours as they are |
| Default | Always on | Off | On, 2025, 70% opacity, smooth display |

At 70% opacity, the basemap's roads and the terrain relief stay faintly visible through the land cover. Lowering the opacity shows more of both.

## Limitations

- **A fixed copy.** The tiles are a snapshot of version 2.0.0 made on 8 November 2026. If DEA reissues the product, `dea-tiles` and `dea-verify` need to be run again.
- **Edge pixels.** A tile pixel is either fully kept or fully transparent, so the clipped edge is stepped at the tile-pixel size: about 8 m at zoom 14, but about 1 km at zoom 7.
- **Class edges in the tiles.** About 0.2–0.4% of zoom 13–14 tile pixels sit on a class edge and show the neighbouring 30 m cell's class (see *Verification*). This is a sub-pixel position difference, not a change of class.
- **Phone screens.** On a 375 px wide screen, the panel covers part of the northern Gold Coast at the startup view. The startup framing was left unchanged.
- **Tilted views.** In tilted views (right-drag or two-finger tilt), distant tiles are drawn smaller than their size. The GPU's minification filter can then blend class colours near the horizon, even with Smooth display off. The same can happen if the browser is zoomed out below 100%. Top-down views at normal browser zoom are unaffected, including after the map has been tilted and returned. With anisotropic filtering off, distant tiles in tilted views also look slightly softer than MapLibre's default would draw them.
- **Below zoom 7** no land cover is drawn.
- **Partial failures.** If a tile fails, the tiles that did load stay visible and the message shows. Until **Try again** is pressed, gaps from failed tiles could be mistaken for no data.

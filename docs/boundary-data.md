# Gold Coast boundary data

The study area outline is the City of Gold Coast local government area (LGA) from the Queensland Government's *Local government area boundaries – Queensland* dataset. The web app reads it from [`public/data/gold-coast-boundary.geojson`](../public/data/gold-coast-boundary.geojson).

## Source

| Item | Value |
| --- | --- |
| Dataset | Local government area boundaries – Queensland |
| Catalogue page | https://www.data.qld.gov.au/dataset/local-government-area-boundaries-queensland |
| Publisher | Department of Natural Resources and Mines, Manufacturing and Regional and Rural Development (Queensland) |
| Dataset metadata last modified | 18 October 2026 (from the catalogue API) |
| Resource used | *Local government area boundaries – Queensland – REST Service*, listed on the catalogue page |
| Service layer | `https://spatial-gis.information.qld.gov.au/arcgis/rest/services/Boundaries/AdministrativeBoundaries/MapServer/1` (layer name "Local government") |
| Feature selected | `lga_code = '3430'` → `lga` "Gold Coast City", `abbrev_name` "GOLD COAST" |
| Stored coordinate system | GDA2020 geographic, EPSG:7844 (from the layer's `sourceSpatialReference`) |
| Retrieved | 3 November 2026 |

The catalogue also lists a bulk download (SHP, TAB, FGDB, KMZ, GPKG), but that goes through the QSpatial ordering form, which emails a link. The REST service is the same dataset's machine-readable endpoint, so the extraction can be repeated without manual steps.

## Licence and attribution

The dataset is released under [Creative Commons Attribution 4.0 (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/). The service gives this copyright line:

> © State of Queensland (Department of Natural Resources and Mines, Manufacturing and Regional and Rural Development) 2026

The map shows this attribution in the bottom-right corner as "Boundary: © State of Queensland, CC BY 4.0", next to the basemap attribution. Both links point to the catalogue page and the licence. The boundary has not been changed in shape. The conversion steps below are all lossless.

## How the file was produced

Run `npm run data:boundary`. The script is [`scripts/extract-gold-coast-boundary.mjs`](../scripts/extract-gold-coast-boundary.mjs), and it runs in plain Node.js with no extra packages.

1. It queries the service layer for `lga_code = '3430'`, with `outSR=7844` (the layer's own coordinate system, so the server does no reprojection) and `f=geojson`. No `maxAllowableOffset` is sent, so the server returns the full-resolution geometry rather than a generalised one.
2. It checks that exactly one feature came back, that the server did not report a transfer limit, and that the geometry is a `Polygon` or `MultiPolygon`. Both types are handled, so any additional parts in a future release would be kept.
3. It rounds every coordinate to 9 decimal places. The layer stores coordinates on a 1e-9 degree grid, so this only removes floating-point noise such as `153.25851426800011` → `153.258514268`. The largest change was 1.1e-13 degrees, far below a millimetre.
4. It checks every ring against the rules in [RFC 7946](https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.6): outer rings counter-clockwise, holes clockwise. It would reverse any ring that breaks this rule. None needed reversing, because the service's GeoJSON output already follows it.
5. It checks that every polygon and ring kept its vertex count, that every ring is still closed, and that rounding did not create repeated consecutive vertices. The script stops with an error if any check fails.
6. It writes a compact GeoJSON `FeatureCollection` with one feature and the attributes `lga`, `abbrev_name`, `lga_code` and `ca_area_sqkm`. The legacy `crs` member that the service adds is left out, because RFC 7946 removed it.

Output of the run used for this milestone:

```
Feature: Gold Coast City (LGA code 3430)
Geometry type: Polygon
Polygons: 1
Rings per polygon: 1
Vertices: 5646
Rings reversed for RFC 7946 winding: 0
Largest coordinate change from rounding: 1.14e-13 degrees
Extent: 153.168916182, -28.26511344, 153.551945912, -27.690382825
Wrote 168329 bytes to ...\public\data\gold-coast-boundary.geojson
```

An independent download of the same feature in Esri JSON format also had exactly one ring with 5,646 vertices, so the GeoJSON conversion on the server drops nothing.

### Why the boundary is a single polygon

The official Gold Coast LGA is one ring with no holes. The boundary runs through the Gold Coast Broadwater and the Jumpinpin channel rather than along each shoreline, so South Stradbroke Island and the Broadwater islands sit inside that one outline. The southern edge follows the Queensland–New South Wales border.

## Coordinate decisions

MapLibre GL JS treats GeoJSON coordinates as WGS84 longitude and latitude. The file keeps the original GDA2020 values without any datum transformation. GDA2020 matched the international reference frame in 2020. Since then Australia's continental drift (about 7 cm per year) has moved it roughly half a metre away from current WGS84. That is far smaller than a screen pixel at any zoom level this project uses. Leaving the values as published avoids adding a transformation step that would change the official numbers. Later raster work, such as imagery and terrain, should note the datum when exact registration matters.

## Size and loading decisions

- **No simplification.** The full geometry is 168 KB uncompressed (about 55 KB with the gzip compression most static hosts apply). That is small enough to load whole, so every official vertex is kept.
- **Display simplification only.** MapLibre's GeoJSON source simplifies lines for drawing at each zoom level (its default `tolerance`). That affects only what is drawn on screen, never the data file.
- **Loaded as a separate static file, not bundled into JavaScript.** The file lives in `public/data/`. Vite copies `public/` unchanged into the build output, so the boundary is cached separately from the app code and can be replaced without rebuilding JavaScript. The app builds its URL from `import.meta.env.BASE_URL`, so it will still resolve when the site is later served from a GitHub Pages sub-path.
- **Fetched once.** The app downloads the file a single time. It uses the same parsed object both to calculate the startup bounds and as the map source data, so MapLibre does not request it again.

# Terrain shading

The **Terrain** toggle draws MapLibre's 2D `hillshade` layer from Mapterhorn elevation tiles. The code is in [`src/map/terrainShading.ts`](../src/map/terrainShading.ts) and [`src/components/GoldCoastMap.tsx`](../src/components/GoldCoastMap.tsx).

## Provider: Mapterhorn

Mapterhorn is an open-data project that publishes global terrain tiles built from public elevation datasets. It is maintained by Oliver Wipfli and supported by the NGI0 Core Fund via NLnet, with hosting and bandwidth donated by Cloudflare. All facts below were checked on 4 November 2026.

| Item | Value | Where it comes from |
| --- | --- | --- |
| TileJSON | `https://tiles.mapterhorn.com/tilejson.json` | https://mapterhorn.com/data-access |
| Tile URL | `https://tiles.mapterhorn.com/{z}/{x}/{y}.webp` | TileJSON |
| Encoding | Terrarium (elevation stored in the red, green and blue values of each pixel) | TileJSON and the data-access page |
| Tile size | 512 × 512 px WebP | TileJSON |
| Required attribution | `<a href='https://mapterhorn.com/attribution'>© Mapterhorn</a>` | TileJSON `attribution` field |
| Code licence | BSD-3-Clause | GitHub repository |
| Data licences | Per source dataset, listed at https://mapterhorn.com/attribution and in https://download.mapterhorn.com/attribution.json | Attribution page |
| API key | None | No key appears in the TileJSON or examples |
| Browser access | `Access-Control-Allow-Origin: *` | Response headers |
| Caching | `Cache-Control: public, max-age=604800` (7 days) | Tile response headers |

**Usage terms.** Mapterhorn publishes no rate limits, fair-use policy or service-level agreement. The site, README and data-access page say nothing on these topics. Its own MapLibre examples load the public endpoint directly from the browser, which is how this app uses it. Before a high-traffic deployment, recheck the site or ask the maintainers. Hosting a copy is also possible, because Mapterhorn publishes PMTiles archives at https://download.mapterhorn.com/ for self-hosting.

**Privacy.** Elevation tiles are requested directly by each visitor's browser. Mapterhorn's privacy policy (updated 7 July 2026) says it stores request details for up to 30 days. These include IP address, referrer, user agent, network (ASN), the Cloudflare location that served the request, and the requested path. This happens only after a visitor switches Terrain on.

### Sources behind the Gold Coast tiles

From `attribution.json`:

| Source | Producer | Licence | Resolution |
| --- | --- | --- | --- |
| Digital Elevation Model (DEM) of Australia derived from LiDAR 5 Metre Grid (Mapterhorn sources `au5a`–`au5i`) | Geoscience Australia | CC BY 4.0 | 5 m |
| Copernicus GLO-30 (`glo30`, the global baseline) | DLR e.V., Airbus Defence and Space, provided under Copernicus by the EU and ESA | Copernicus full, free and open licence | 30 m |

CC BY 4.0 allows attribution through a link to a page that lists the sources. Mapterhorn's "© Mapterhorn" link does this. The app shows the same text and link, set as a fixed string in [`terrainShading.ts`](../src/map/terrainShading.ts) rather than read from the TileJSON at run time, so a change on Mapterhorn's server cannot alter what the page displays. The link opens in a new tab.

### Coverage checked for this project

Tile requests made on 4 November 2026:

| Zoom | Springbrook, Tamborine, Beaudesert (land) | Surfers Paradise (coast) | Offshore |
| --- | --- | --- | --- |
| 8–12 | 200 | 200 | 200 (tiny flat tile) |
| 13–14 | 200 | 200 | 404 |
| 15–17 | 404 | 404 | 404 |

Elevation detail over the Gold Coast therefore stops at **zoom 14** (about 4 m per pixel at this latitude), which matches the 5 m LiDAR source. Mapterhorn's TileJSON does not state a maximum zoom, so MapLibre would otherwise assume 22 and request tiles that do not exist. The source sets `maxzoom: 14`. Beyond that zoom, MapLibre enlarges the zoom-14 tiles instead of requesting new ones.

## How it works

### React state

`GoldCoastMap` keeps `terrainStatus` in React state, as `'off'`, `'on'` or `'unavailable'`. It starts as `'off'`.

- The button's `aria-pressed` is `true` only when the status is `'on'`. Screen readers announce it as a toggle button that is "pressed" or "not pressed". The CSS styles the switch from that same attribute, so what you see always matches what assistive technology reports.
- `toggleTerrainShading` calls `showTerrainShading` or `hideTerrainShading` on the map, then updates the state. React then re-renders the button and notice.
- The button is disabled until the basemap has loaded, the same as Reset.

### Loading once and reusing

The first time Terrain is switched on, `showTerrainShading`:

1. Adds a `raster-dem` source pointing at Mapterhorn's TileJSON, with `encoding: 'terrarium'`, `maxzoom: 14` and a fixed attribution. MapLibre fetches the TileJSON, takes the tile URL and tile size from it, and keeps the three values set here. Settings passed directly to a source override the TileJSON.
2. Adds the `hillshade` layer below the first water layer (see *Layer position*).

After that, switching off sets the layer's `visibility` to `none` and switching on sets it back to `visible`. The source and layer stay on the map, and the TileJSON is never fetched again.

MapLibre does reload the elevation tiles when the layer is shown again. That happens for any layer change on a `raster-dem` source. The tiles still come from the browser's HTTP cache. Measured with Chrome DevTools Protocol, the first switch-on downloaded 13 files (1.13 MB). Later switch-ons were served entirely from the disk cache, with 0 bytes over the network. While Terrain is off, no elevation tiles are requested at all, even when you pan to new areas.

### From tile to shading

1. MapLibre requests the 512 px WebP tiles covering the view and decodes them in its web worker.
2. With Terrarium encoding, each pixel stores height as `elevation = red × 256 + green + blue ÷ 256 − 32768` metres.
3. The worker turns each tile into a grid of heights. It borrows a one-pixel border from neighbouring tiles, so slopes are continuous across tile edges.
4. On the graphics card, the `hillshade` layer works out each pixel's slope and which way it faces from the neighbouring heights. It compares that with the light direction and darkens slopes facing away from the light.
5. The result is blended over the layers beneath it.

Nothing about the camera changes. The layer is purely 2D and the app never calls `setTerrain`, so the map stays top-down and the toggle cannot alter position, zoom, bearing or pitch.

### Layer position

The OpenFreeMap Liberty style draws, in order:
1. background and land fills (parks, residential land, wood, grass)
2. waterways and water
3. sand, airports, tunnels, roads, bridges, buildings
4. admin boundaries
5. labels

The shading is inserted **directly below the first layer whose `source-layer` is `waterway` or `water`**. The lookup uses `source-layer` rather than a layer id, so it keeps working if the style renames its layers. If no water layer exists, it falls back to the first label layer. As a result:

- Parks, bushland and residential land are shaded, which is where the relief is.
- The sea, rivers, lakes and canals draw on top as flat blue. That matters on the Gold Coast, where the coast and canal estates are a large part of the map.
- Roads, buildings, the Gold Coast boundary and every label stay above the shading at full strength.

### Shading settings

| Property | Value | Reason |
| --- | --- | --- |
| `hillshade-method` | `igor` | MapLibre describes it as the method that "tries to minimize effects on other map features beneath" (like GDAL's `gdaldem -igor`). In the screenshots, flat coastal suburbs, canals and roads kept their original colours, while the hinterland ranges gained clear relief. |
| `hillshade-exaggeration` | 0.45 at zoom 8 → 0.3 at zoom 12 → 0.22 at zoom 15 | Stronger at regional scale, where slopes cover few pixels, and gentler up close, where 5 m LiDAR shows every gully. I softened the first version by about 25% after reviewing Springbrook at zoom 13. |
| `hillshade-illumination-direction` | 315° | Light from the north-west (upper left), the cartographic convention that makes ridges read as raised rather than sunken. |
| `hillshade-illumination-anchor` | `viewport` (default) | The light stays at the upper left of the screen when the map is rotated, so relief never appears inverted. |
| `hillshade-shadow-color` / `accent-color` | `#3a4552` | A desaturated slate, softer than black, which avoids muddying the greens and beiges of the basemap. |
| `hillshade-highlight-color` | `#ffffff` | Default |

I checked these settings in screenshots at five places:
- the regional startup view (about zoom 9)
- Tamborine escarpment (about zoom 12)
- Springbrook (about zoom 13)
- Surfers Paradise (about zoom 13)
- Burleigh Heads (about zoom 14)

### Failure handling

MapLibre reports problems through `error` events on the map. Events from a source carry a `sourceId`.

- **Real failures** include no connection, DNS failure, blocked requests, a failed TileJSON and HTTP 5xx tiles. MapLibre raises an `error` event for each. When the event comes from the elevation source and the layer is visible, the app:
  1. hides the layer, so no patchy partial shading is left behind
  2. sets the status to `'unavailable'`
  3. shows "Terrain shading is unavailable right now. The street map still works." in a `role="status"` live region, which screen readers announce politely
- **Missing tiles (HTTP 404)** are normal. Mapterhorn returns 404 offshore beyond zoom 12 and everywhere beyond zoom 14. MapLibre treats a 404 as "no data here", stays silent, and draws from the nearest lower-zoom tile. The app shows no message for these.
- **Retrying.** Pressing Terrain while the status is `'unavailable'` removes the failed source and layer and adds them again. MapLibre retries from scratch, so shading returns once the connection is back.
- **Other map errors.** Adding an `error` listener stops MapLibre from writing errors to the console by itself. The listener therefore writes every non-terrain error to the console itself, so basemap problems stay visible.
- **Limitation.** If Mapterhorn ever returned 404 for every tile, the toggle would show on with no shading and no message. A 404 cannot be told apart from normal "no data here" responses.

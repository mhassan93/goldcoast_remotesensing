import type { ErrorEvent, Map as MapLibreMap } from 'maplibre-gl'

export const terrainSourceId = 'mapterhorn-elevation'
export const terrainShadingLayerId = 'terrain-shading'

const mapterhornTileJsonUrl = 'https://tiles.mapterhorn.com/tilejson.json'
const mapterhornAttribution =
  '<a href="https://mapterhorn.com/attribution" target="_blank" rel="noopener">© Mapterhorn</a>'
const highestElevationZoomOverAustralia = 14
const sourceLayersDrawnAboveShading = new Set(['waterway', 'water'])

export type MapErrorEvent = ErrorEvent & { sourceId?: string }

function findLayerToInsertShadingBelow(map: MapLibreMap) {
  const styleLayers = map.getStyle().layers
  const firstWaterLayer = styleLayers.find(
    (layer) => 'source-layer' in layer && sourceLayersDrawnAboveShading.has(layer['source-layer'] ?? ''),
  )
  return firstWaterLayer?.id ?? styleLayers.find((layer) => layer.type === 'symbol')?.id
}

export function showTerrainShading(map: MapLibreMap) {
  if (!map.getSource(terrainSourceId)) {
    map.addSource(terrainSourceId, {
      type: 'raster-dem',
      url: mapterhornTileJsonUrl,
      encoding: 'terrarium',
      maxzoom: highestElevationZoomOverAustralia,
      attribution: mapterhornAttribution,
    })
  }

  if (!map.getLayer(terrainShadingLayerId)) {
    map.addLayer(
      {
        id: terrainShadingLayerId,
        type: 'hillshade',
        source: terrainSourceId,
        paint: {
          'hillshade-method': 'igor',
          'hillshade-illumination-direction': 315,
          'hillshade-exaggeration': ['interpolate', ['linear'], ['zoom'], 8, 0.45, 12, 0.3, 15, 0.22],
          'hillshade-shadow-color': '#3a4552',
          'hillshade-highlight-color': '#ffffff',
          'hillshade-accent-color': '#3a4552',
        },
      },
      findLayerToInsertShadingBelow(map),
    )
  }

  map.setLayoutProperty(terrainShadingLayerId, 'visibility', 'visible')
}

export function hideTerrainShading(map: MapLibreMap) {
  if (map.getLayer(terrainShadingLayerId)) {
    map.setLayoutProperty(terrainShadingLayerId, 'visibility', 'none')
  }
}

export function removeTerrainShading(map: MapLibreMap) {
  if (map.getLayer(terrainShadingLayerId)) {
    map.removeLayer(terrainShadingLayerId)
  }
  if (map.getSource(terrainSourceId)) {
    map.removeSource(terrainSourceId)
  }
}

export function isTerrainShadingVisible(map: MapLibreMap) {
  return (
    Boolean(map.getLayer(terrainShadingLayerId)) &&
    map.getLayoutProperty(terrainShadingLayerId, 'visibility') !== 'none'
  )
}

export function isTerrainSourceError(event: MapErrorEvent) {
  return event.sourceId === terrainSourceId
}

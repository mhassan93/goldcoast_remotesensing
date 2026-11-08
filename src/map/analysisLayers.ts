import type { Map as MapLibreMap, RasterSourceSpecification, RasterTileSource } from 'maplibre-gl'
import { boundaryOutlineLayerId } from './boundaryOutline.ts'
import {
  deaLandCoverAttribution,
  deaLandCoverBounds,
  deaLandCoverMaxZoom,
  deaLandCoverMinZoom,
  deaLandCoverTileSize,
  deaLandCoverTileUrl,
  landCoverYears,
  type LandCoverYear,
} from './deaLandCover.ts'
import {
  findSentinelLayer,
  sentinelAttribution,
  sentinelTileUrl,
  sentinelViews,
  sentinelYears,
  type SentinelIndexMetadata,
  type SentinelView,
  type SentinelYear,
} from './sentinelIndexLayers.ts'

type DeaLayerKey = `dea-${LandCoverYear}`

export type AnalysisLayerKey = DeaLayerKey | `sentinel-${SentinelYear}-${SentinelView}`

type DisplayResampling = 'linear' | 'nearest'

export type AnalysisLayerDefinition = {
  key: AnalysisLayerKey
  source: RasterSourceSpecification
  isCategorical: boolean
  minZoom: number
  fixedResampling: DisplayResampling | null
}

const deaLayerKeys: DeaLayerKey[] = landCoverYears.map((year) => `dea-${year}` as const)

const analysisLayerKeys: AnalysisLayerKey[] = [
  ...deaLayerKeys,
  ...sentinelYears.flatMap((year) => sentinelViews.map((view) => `sentinel-${year}-${view}` as const)),
]

function analysisSourceId(key: AnalysisLayerKey) {
  return `analysis-${key}`
}

function analysisLayerId(key: AnalysisLayerKey) {
  return `analysis-${key}-layer`
}

export function deaLayerDefinition(year: LandCoverYear): AnalysisLayerDefinition {
  return {
    key: `dea-${year}`,
    isCategorical: true,
    minZoom: deaLandCoverMinZoom,
    fixedResampling: null,
    source: {
      type: 'raster',
      tiles: [deaLandCoverTileUrl(year)],
      tileSize: deaLandCoverTileSize,
      minzoom: deaLandCoverMinZoom,
      maxzoom: deaLandCoverMaxZoom,
      bounds: deaLandCoverBounds,
      attribution: deaLandCoverAttribution,
    },
  }
}

export function sentinelLayerDefinition(
  metadata: SentinelIndexMetadata,
  year: SentinelYear,
  view: SentinelView,
): AnalysisLayerDefinition {
  const layer = findSentinelLayer(metadata, view)
  const isCategorical = layer.kind === 'categorical'
  return {
    key: `sentinel-${year}-${view}`,
    isCategorical,
    minZoom: metadata.min_zoom,
    fixedResampling: isCategorical ? 'nearest' : 'linear',
    source: {
      type: 'raster',
      tiles: [sentinelTileUrl(year, layer)],
      tileSize: metadata.tile_size,
      minzoom: metadata.min_zoom,
      maxzoom: metadata.max_zoom,
      bounds: metadata.bounds,
      attribution: sentinelAttribution(metadata),
    },
  }
}

export function findAnalysisLayerKeyForSource(sourceId: string | undefined) {
  return analysisLayerKeys.find((key) => analysisSourceId(key) === sourceId)
}

function findLayerToInsertAnalysisBelow(map: MapLibreMap) {
  if (map.getLayer(boundaryOutlineLayerId)) {
    return boundaryOutlineLayerId
  }
  return map.getStyle().layers.find((layer) => layer.type === 'symbol')?.id
}

function displayResampling(isDisplaySmoothed: boolean): DisplayResampling {
  return isDisplaySmoothed ? 'linear' : 'nearest'
}

function addAnalysisLayer(
  map: MapLibreMap,
  definition: AnalysisLayerDefinition,
  opacity: number,
  isDisplaySmoothed: boolean,
) {
  const sourceId = analysisSourceId(definition.key)
  map.addSource(sourceId, definition.source)

  const source = map.getSource<RasterTileSource>(sourceId)
  if (source) {
    source.roundZoom = false
  }
  const resampling = definition.fixedResampling ?? displayResampling(isDisplaySmoothed)

  map.addLayer(
    {
      id: analysisLayerId(definition.key),
      type: 'raster',
      source: sourceId,
      minzoom: definition.minZoom,
      layout: {
        visibility: 'none',
      },
      paint: definition.isCategorical
        ? { 'raster-opacity': opacity, 'raster-resampling': resampling, 'raster-fade-duration': 0 }
        : { 'raster-opacity': opacity, 'raster-resampling': resampling },
    },
    findLayerToInsertAnalysisBelow(map),
  )
}

export function showAnalysisLayer(
  map: MapLibreMap,
  definition: AnalysisLayerDefinition,
  opacity: number,
  isDisplaySmoothed: boolean,
) {
  for (const key of analysisLayerKeys) {
    if (key !== definition.key && map.getLayer(analysisLayerId(key))) {
      map.setLayoutProperty(analysisLayerId(key), 'visibility', 'none')
    }
  }

  if (!map.getSource(analysisSourceId(definition.key))) {
    addAnalysisLayer(map, definition, opacity, isDisplaySmoothed)
  }

  map.setLayoutProperty(analysisLayerId(definition.key), 'visibility', 'visible')
}

export function hideAnalysisLayers(map: MapLibreMap) {
  for (const key of analysisLayerKeys) {
    if (map.getLayer(analysisLayerId(key))) {
      map.setLayoutProperty(analysisLayerId(key), 'visibility', 'none')
    }
  }
}

export function setAnalysisLayerOpacity(map: MapLibreMap, opacity: number) {
  for (const key of analysisLayerKeys) {
    if (map.getLayer(analysisLayerId(key))) {
      map.setPaintProperty(analysisLayerId(key), 'raster-opacity', opacity)
    }
  }
}

export function setAnalysisLayerSmoothing(map: MapLibreMap, isDisplaySmoothed: boolean) {
  for (const key of deaLayerKeys) {
    if (map.getLayer(analysisLayerId(key))) {
      map.setPaintProperty(analysisLayerId(key), 'raster-resampling', displayResampling(isDisplaySmoothed))
    }
  }
}

export function removeAnalysisLayer(map: MapLibreMap, key: AnalysisLayerKey) {
  if (map.getLayer(analysisLayerId(key))) {
    map.removeLayer(analysisLayerId(key))
  }
  if (map.getSource(analysisSourceId(key))) {
    map.removeSource(analysisSourceId(key))
  }
}

export function isAnalysisLayerLoaded(map: MapLibreMap, key: AnalysisLayerKey) {
  return Boolean(map.getSource(analysisSourceId(key))) && map.isSourceLoaded(analysisSourceId(key))
}

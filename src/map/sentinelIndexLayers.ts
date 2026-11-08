import { publicDataTileUrl, publicDataUrl } from './publicData.ts'

export const sentinelYears = [2020, 2025] as const

export type SentinelYear = (typeof sentinelYears)[number]

export const defaultSentinelYear: SentinelYear = 2025

export const sentinelViews = ['classes', 'ndvi', 'ndbi', 'mndwi'] as const

export type SentinelView = (typeof sentinelViews)[number]

export type SentinelClass = {
  value: number
  name: string
  color: string
}

export type SentinelCategoricalLayer = {
  id: 'classes'
  kind: 'categorical'
  title: string
  path: string
  classes: SentinelClass[]
}

export type SentinelContinuousLayer = {
  id: Exclude<SentinelView, 'classes'>
  kind: 'continuous'
  title: string
  formula: string
  path: string
  range: [number, number]
  stops: [number, string][]
  steps: number
}

export type SentinelLayer = SentinelCategoricalLayer | SentinelContinuousLayer

export type SentinelIndexMetadata = {
  title: string
  source: {
    product: string
    provider: string
    stac_collection: string
    attribution: string
    processing_baseline: string
  }
  period: { start: string; end: string; first_acquisition: string; last_acquisition: string }
  acquisitions_used: number
  composite: string
  resolution_m: number
  grid_crs: string
  minimum_valid_observations: number
  tile_size: number
  min_zoom: number
  max_zoom: number
  bounds: [number, number, number, number]
  layers: SentinelLayer[]
}

export type SentinelMetadataByYear = Partial<Record<SentinelYear, SentinelIndexMetadata>>

export const sentinelViewLabels: Record<SentinelView, string> = {
  classes: 'Classes',
  ndvi: 'NDVI',
  ndbi: 'NDBI',
  mndwi: 'MNDWI',
}

function sentinelDataPath(year: SentinelYear) {
  return `sentinel2-${year}/`
}

export async function loadSentinelIndexMetadata(
  year: SentinelYear,
  signal: AbortSignal,
): Promise<SentinelIndexMetadata> {
  const response = await fetch(`${publicDataUrl}${sentinelDataPath(year)}layers.json`, { signal })
  if (!response.ok) {
    throw new Error(`Sentinel-2 ${year} layer metadata request failed with HTTP ${response.status}`)
  }
  const metadata = (await response.json()) as SentinelIndexMetadata
  const missingViews = sentinelViews.filter((view) => !metadata.layers.some((layer) => layer.id === view))
  if (missingViews.length > 0) {
    throw new Error(`Sentinel-2 ${year} layer metadata is missing ${missingViews.join(', ')}`)
  }
  return metadata
}

export function findSentinelLayer(metadata: SentinelIndexMetadata, view: SentinelView) {
  const layer = metadata.layers.find((candidate) => candidate.id === view)
  if (!layer) {
    throw new Error(`Sentinel-2 layer ${view} is not in the metadata`)
  }
  return layer
}

export function sentinelTileUrl(year: SentinelYear, layer: SentinelLayer) {
  return publicDataTileUrl(`${sentinelDataPath(year)}${layer.path}`)
}

function escapeHtmlText(text: string) {
  return text.replace(/[&<>"']/g, (character) => `&#${character.charCodeAt(0)};`)
}

export function sentinelAttribution(metadata: SentinelIndexMetadata) {
  return `Index analysis: this project, ${escapeHtmlText(metadata.source.attribution)}`
}

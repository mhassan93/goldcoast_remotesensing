import type { FeatureCollection, MultiPolygon, Polygon } from 'geojson'
import type { LngLatBoundsLike } from 'maplibre-gl'

export type BoundaryFeatureCollection = FeatureCollection<Polygon | MultiPolygon>

export const goldCoastBoundaryUrl = `${import.meta.env.BASE_URL}data/gold-coast-boundary.geojson`

export async function loadGoldCoastBoundary(signal: AbortSignal): Promise<BoundaryFeatureCollection> {
  const response = await fetch(goldCoastBoundaryUrl, { signal })
  if (!response.ok) {
    throw new Error(`Boundary request failed with HTTP ${response.status}`)
  }
  return (await response.json()) as BoundaryFeatureCollection
}

export function calculateBoundaryBounds(boundary: BoundaryFeatureCollection): LngLatBoundsLike {
  let west = Infinity
  let south = Infinity
  let east = -Infinity
  let north = -Infinity

  for (const feature of boundary.features) {
    const polygons =
      feature.geometry.type === 'Polygon' ? [feature.geometry.coordinates] : feature.geometry.coordinates
    for (const polygon of polygons) {
      for (const ring of polygon) {
        for (const [longitude, latitude] of ring) {
          west = Math.min(west, longitude)
          south = Math.min(south, latitude)
          east = Math.max(east, longitude)
          north = Math.max(north, latitude)
        }
      }
    }
  }

  if (!Number.isFinite(west)) {
    throw new Error('Boundary data contains no coordinates')
  }

  return [
    [west, south],
    [east, north],
  ]
}

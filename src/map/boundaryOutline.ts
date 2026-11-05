import type { Map as MapLibreMap } from 'maplibre-gl'
import type { BoundaryFeatureCollection } from './boundary.ts'

export const boundarySourceId = 'gold-coast-boundary'
export const boundaryOutlineLayerId = 'gold-coast-boundary-outline'

const boundaryAttribution =
  'Boundary: <a href="https://www.data.qld.gov.au/dataset/local-government-area-boundaries-queensland" target="_blank" rel="noopener">© State of Queensland</a>, <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noopener">CC BY 4.0</a>'

export function addBoundaryOutline(map: MapLibreMap, boundary: BoundaryFeatureCollection) {
  map.addSource(boundarySourceId, {
    type: 'geojson',
    data: boundary,
    attribution: boundaryAttribution,
  })

  const firstLabelLayerId = map.getStyle().layers.find((layer) => layer.type === 'symbol')?.id

  map.addLayer(
    {
      id: boundaryOutlineLayerId,
      type: 'line',
      source: boundarySourceId,
      layout: {
        'line-join': 'round',
        'line-cap': 'round',
      },
      paint: {
        'line-color': '#4c2a85',
        'line-opacity': 0.8,
        'line-width': ['interpolate', ['linear'], ['zoom'], 8, 2, 12, 3, 16, 4],
      },
    },
    firstLabelLayerId,
  )
}

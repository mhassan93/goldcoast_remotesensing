import type { FitBoundsOptions } from 'maplibre-gl'

const minimumEdgePadding = 16
const maximumEdgePadding = 48
const edgePaddingShareOfShortestSide = 0.06
const minimumToolbarClearance = 48
const attributionClearance = 28

export function getRegionalFramingOptions(
  mapContainer: HTMLElement,
  mapToolbar: HTMLElement | null,
): FitBoundsOptions {
  const shortestSide = Math.min(mapContainer.clientWidth, mapContainer.clientHeight)
  const edgePadding = Math.round(
    Math.min(Math.max(shortestSide * edgePaddingShareOfShortestSide, minimumEdgePadding), maximumEdgePadding),
  )
  const toolbarBottomWithinMap = mapToolbar
    ? mapToolbar.getBoundingClientRect().bottom - mapContainer.getBoundingClientRect().top
    : 0
  const toolbarClearance = Math.max(minimumToolbarClearance, Math.ceil(toolbarBottomWithinMap))

  return {
    padding: {
      top: edgePadding + toolbarClearance,
      bottom: edgePadding + attributionClearance,
      left: edgePadding,
      right: edgePadding,
    },
    bearing: 0,
    pitch: 0,
  }
}

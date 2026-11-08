import {
  AttributionControl,
  Map as MapLibreMap,
  NavigationControl,
  ScaleControl,
  type LngLatBoundsLike,
} from 'maplibre-gl'
import { useEffect, useRef, useState } from 'react'
import {
  deaLayerDefinition,
  findAnalysisLayerKeyForSource,
  hideAnalysisLayers,
  isAnalysisLayerLoaded,
  removeAnalysisLayer,
  sentinelLayerDefinition,
  setAnalysisLayerOpacity,
  setAnalysisLayerSmoothing,
  showAnalysisLayer,
  type AnalysisLayerKey,
} from '../map/analysisLayers.ts'
import { openFreeMapStreetStyleUrl } from '../map/basemap.ts'
import { calculateBoundaryBounds, loadGoldCoastBoundary } from '../map/boundary.ts'
import { addBoundaryOutline } from '../map/boundaryOutline.ts'
import { defaultLandCoverYear, type LandCoverYear } from '../map/deaLandCover.ts'
import { getRegionalFramingOptions } from '../map/regionalFraming.ts'
import {
  defaultSentinelYear,
  loadSentinelIndexMetadata,
  sentinelYears,
  type SentinelMetadataByYear,
  type SentinelView,
  type SentinelYear,
} from '../map/sentinelIndexLayers.ts'
import {
  hideTerrainShading,
  isTerrainShadingVisible,
  isTerrainSourceError,
  removeTerrainShading,
  showTerrainShading,
  type MapErrorEvent,
} from '../map/terrainShading.ts'
import {
  AnalysisLayerPanel,
  type AnalysisDisplayStatus,
  type AnalysisSelection,
  type AnalysisSource,
  type SentinelMetadataStatus,
} from './AnalysisLayerPanel.tsx'

type MapStatus = 'loading' | 'ready' | 'error'
type TerrainStatus = 'off' | 'on' | 'unavailable'
type AnalysisLoad = { key: AnalysisLayerKey; status: 'loading' | 'ready' | 'error' }
type ActiveAnalysisLayer = { key: AnalysisLayerKey; minZoom: number }

const defaultAnalysisOpacity = 0.7
const isDisplaySmoothedByDefault = true
const pitchThatNeverEnablesAnisotropicFiltering = 180
const defaultAnalysisSelection: AnalysisSelection = {
  isEnabled: true,
  source: 'dea',
  deaYear: defaultLandCoverYear,
  sentinelYear: defaultSentinelYear,
  sentinelView: 'classes',
}

function selectedLayerDefinition(selection: AnalysisSelection, sentinelMetadata: SentinelMetadataByYear) {
  if (selection.source === 'dea') {
    return deaLayerDefinition(selection.deaYear)
  }
  const metadata = sentinelMetadata[selection.sentinelYear]
  return metadata ? sentinelLayerDefinition(metadata, selection.sentinelYear, selection.sentinelView) : null
}

export function GoldCoastMap() {
  const mapContainerRef = useRef<HTMLDivElement>(null)
  const mapToolbarRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<MapLibreMap | null>(null)
  const boundaryBoundsRef = useRef<LngLatBoundsLike | null>(null)
  const activeAnalysisLayerRef = useRef<ActiveAnalysisLayer | null>(null)
  const failedAnalysisLayersRef = useRef(new Set<AnalysisLayerKey>())
  const [mapStatus, setMapStatus] = useState<MapStatus>('loading')
  const [terrainStatus, setTerrainStatus] = useState<TerrainStatus>('off')
  const [analysisSelection, setAnalysisSelection] = useState<AnalysisSelection>(defaultAnalysisSelection)
  const [analysisOpacity, setAnalysisOpacity] = useState(defaultAnalysisOpacity)
  const [isDisplaySmoothed, setIsDisplaySmoothed] = useState(isDisplaySmoothedByDefault)
  const [analysisLoad, setAnalysisLoad] = useState<AnalysisLoad>({
    key: `dea-${defaultLandCoverYear}`,
    status: 'loading',
  })
  const [zoomLevel, setZoomLevel] = useState(0)
  const [sentinelMetadata, setSentinelMetadata] = useState<SentinelMetadataByYear>({})
  const [sentinelMetadataStatus, setSentinelMetadataStatus] = useState<SentinelMetadataStatus>('loading')

  useEffect(() => {
    const metadataRequest = new AbortController()
    Promise.allSettled(sentinelYears.map((year) => loadSentinelIndexMetadata(year, metadataRequest.signal))).then(
      (results) => {
        if (metadataRequest.signal.aborted) {
          return
        }
        const loadedMetadata: SentinelMetadataByYear = {}
        results.forEach((result, position) => {
          if (result.status === 'fulfilled') {
            loadedMetadata[sentinelYears[position]] = result.value
          } else {
            console.error(result.reason)
          }
        })
        setSentinelMetadata(loadedMetadata)
        setSentinelMetadataStatus(Object.keys(loadedMetadata).length > 0 ? 'ready' : 'unavailable')
      },
    )
    return () => metadataRequest.abort()
  }, [])

  useEffect(() => {
    const mapContainer = mapContainerRef.current
    if (!mapContainer) {
      return
    }

    const boundaryRequest = new AbortController()
    let createdMap: MapLibreMap | null = null

    loadGoldCoastBoundary(boundaryRequest.signal)
      .then((boundary) => {
        if (boundaryRequest.signal.aborted) {
          return
        }

        const boundaryBounds = calculateBoundaryBounds(boundary)
        const map = new MapLibreMap({
          container: mapContainer,
          style: openFreeMapStreetStyleUrl,
          bounds: boundaryBounds,
          fitBoundsOptions: getRegionalFramingOptions(mapContainer, mapToolbarRef.current),
          attributionControl: false,
          anisotropicFilterPitch: pitchThatNeverEnablesAnisotropicFiltering,
        })

        map.addControl(new NavigationControl(), 'top-right')
        map.addControl(new AttributionControl({ compact: false }), 'bottom-right')
        map.addControl(new ScaleControl({ unit: 'metric' }), 'bottom-right')

        const isActiveAnalysisLayer = (key: AnalysisLayerKey) => activeAnalysisLayerRef.current?.key === key

        const updateActiveAnalysisLoad = (key: AnalysisLayerKey, status: 'loading' | 'ready') => {
          setAnalysisLoad((current) => (current.key === key && current.status === 'error' ? current : { key, status }))
        }

        map.on('error', (event: MapErrorEvent) => {
          const analysisLayerKey = findAnalysisLayerKeyForSource(event.sourceId)
          if (analysisLayerKey !== undefined) {
            failedAnalysisLayersRef.current.add(analysisLayerKey)
            if (isActiveAnalysisLayer(analysisLayerKey)) {
              setAnalysisLoad({ key: analysisLayerKey, status: 'error' })
            }
            return
          }
          if (!isTerrainSourceError(event)) {
            console.error(event.error)
            return
          }
          if (isTerrainShadingVisible(map)) {
            hideTerrainShading(map)
            setTerrainStatus('unavailable')
          }
        })

        map.on('sourcedataloading', (event) => {
          const analysisLayerKey = findAnalysisLayerKeyForSource(event.sourceId)
          if (analysisLayerKey !== undefined && isActiveAnalysisLayer(analysisLayerKey)) {
            updateActiveAnalysisLoad(analysisLayerKey, 'loading')
          }
        })

        map.on('idle', () => {
          const activeLayer = activeAnalysisLayerRef.current
          if (activeLayer && isAnalysisLayerLoaded(map, activeLayer.key)) {
            updateActiveAnalysisLoad(activeLayer.key, 'ready')
          }
        })

        map.on('zoom', () => {
          setZoomLevel(Math.floor(map.getZoom()))
        })

        map.once('load', () => {
          addBoundaryOutline(map, boundary)
          const definition = deaLayerDefinition(defaultLandCoverYear)
          activeAnalysisLayerRef.current = { key: definition.key, minZoom: definition.minZoom }
          showAnalysisLayer(map, definition, defaultAnalysisOpacity, isDisplaySmoothedByDefault)
          setZoomLevel(Math.floor(map.getZoom()))
          setMapStatus('ready')
        })

        createdMap = map
        mapRef.current = map
        boundaryBoundsRef.current = boundaryBounds
      })
      .catch((error: unknown) => {
        if (boundaryRequest.signal.aborted) {
          return
        }
        console.error(error)
        setMapStatus('error')
      })

    return () => {
      boundaryRequest.abort()
      createdMap?.remove()
      mapRef.current = null
      boundaryBoundsRef.current = null
    }
  }, [])

  const resetToGoldCoast = () => {
    const map = mapRef.current
    const boundaryBounds = boundaryBoundsRef.current
    if (!map || !boundaryBounds) {
      return
    }
    map.fitBounds(boundaryBounds, getRegionalFramingOptions(map.getContainer(), mapToolbarRef.current))
  }

  const toggleTerrainShading = () => {
    const map = mapRef.current
    if (!map) {
      return
    }
    if (terrainStatus === 'on') {
      hideTerrainShading(map)
      setTerrainStatus('off')
      return
    }
    if (terrainStatus === 'unavailable') {
      removeTerrainShading(map)
    }
    showTerrainShading(map)
    setTerrainStatus('on')
  }

  const applyAnalysisSelection = (selection: AnalysisSelection) => {
    const map = mapRef.current
    if (!map) {
      return
    }
    setAnalysisSelection(selection)
    const definition = selectedLayerDefinition(selection, sentinelMetadata)
    if (!selection.isEnabled || !definition) {
      activeAnalysisLayerRef.current = null
      hideAnalysisLayers(map)
      return
    }
    activeAnalysisLayerRef.current = { key: definition.key, minZoom: definition.minZoom }
    if (failedAnalysisLayersRef.current.has(definition.key)) {
      removeAnalysisLayer(map, definition.key)
      failedAnalysisLayersRef.current.delete(definition.key)
    }
    showAnalysisLayer(map, definition, analysisOpacity, isDisplaySmoothed)
    setAnalysisLoad({ key: definition.key, status: 'loading' })
  }

  const toggleAnalysisLayer = () => {
    applyAnalysisSelection({ ...analysisSelection, isEnabled: !analysisSelection.isEnabled })
  }

  const selectAnalysisSource = (source: AnalysisSource) => {
    if (source !== analysisSelection.source) {
      applyAnalysisSelection({ ...analysisSelection, source })
    }
  }

  const selectDeaYear = (deaYear: LandCoverYear) => {
    if (deaYear !== analysisSelection.deaYear) {
      applyAnalysisSelection({ ...analysisSelection, deaYear })
    }
  }

  const selectSentinelYear = (sentinelYear: SentinelYear) => {
    if (sentinelYear !== analysisSelection.sentinelYear) {
      applyAnalysisSelection({ ...analysisSelection, sentinelYear })
    }
  }

  const selectSentinelView = (sentinelView: SentinelView) => {
    if (sentinelView !== analysisSelection.sentinelView) {
      applyAnalysisSelection({ ...analysisSelection, sentinelView })
    }
  }

  const retryAnalysisLayer = () => {
    const activeLayer = activeAnalysisLayerRef.current
    if (activeLayer) {
      failedAnalysisLayersRef.current.add(activeLayer.key)
    }
    applyAnalysisSelection(analysisSelection)
  }

  const changeAnalysisOpacity = (opacity: number) => {
    setAnalysisOpacity(opacity)
    const map = mapRef.current
    if (map) {
      setAnalysisLayerOpacity(map, opacity)
    }
  }

  const toggleDisplaySmoothing = () => {
    const nextIsDisplaySmoothed = !isDisplaySmoothed
    setIsDisplaySmoothed(nextIsDisplaySmoothed)
    const map = mapRef.current
    if (map) {
      setAnalysisLayerSmoothing(map, nextIsDisplaySmoothed)
    }
  }

  const isMapReady = mapStatus === 'ready'
  const activeDefinition = selectedLayerDefinition(analysisSelection, sentinelMetadata)

  const analysisStatus: AnalysisDisplayStatus =
    !analysisSelection.isEnabled || !activeDefinition
      ? 'hidden'
      : analysisLoad.key !== activeDefinition.key
        ? 'loading'
        : analysisLoad.status === 'error'
          ? 'error'
          : zoomLevel < activeDefinition.minZoom
            ? 'zoomed-out'
            : analysisLoad.status

  return (
    <section className="map-panel" aria-label="Map of the City of Gold Coast study area">
      <div className="map-overlay">
        <div ref={mapToolbarRef} className="map-toolbar">
          <button
            type="button"
            className="map-control-button"
            onClick={resetToGoldCoast}
            disabled={!isMapReady}
          >
            Reset to Gold Coast
          </button>
          <button
            type="button"
            className="map-control-button switch-toggle"
            aria-pressed={terrainStatus === 'on'}
            onClick={toggleTerrainShading}
            disabled={!isMapReady}
          >
            <span className="switch-toggle-track" aria-hidden="true" />
            Terrain
          </button>
        </div>
        <div className="map-notice-region" role="status" aria-live="polite">
          {terrainStatus === 'unavailable' && (
            <p className="map-notice">Terrain shading is unavailable right now. The street map still works.</p>
          )}
        </div>
        <AnalysisLayerPanel
          isMapReady={isMapReady}
          selection={analysisSelection}
          opacity={analysisOpacity}
          isDisplaySmoothed={isDisplaySmoothed}
          status={analysisStatus}
          sentinelMetadata={sentinelMetadata}
          sentinelMetadataStatus={sentinelMetadataStatus}
          onToggle={toggleAnalysisLayer}
          onSelectSource={selectAnalysisSource}
          onSelectDeaYear={selectDeaYear}
          onSelectSentinelYear={selectSentinelYear}
          onSelectSentinelView={selectSentinelView}
          onChangeOpacity={changeAnalysisOpacity}
          onToggleDisplaySmoothing={toggleDisplaySmoothing}
          onRetry={retryAnalysisLayer}
        />
      </div>
      <div ref={mapContainerRef} className="map-canvas" />
      {mapStatus === 'loading' && (
        <p className="map-status" role="status">
          Loading map…
        </p>
      )}
      {mapStatus === 'error' && (
        <p className="map-status map-status-error" role="alert">
          The Gold Coast boundary could not be loaded. Refresh the page to try again.
        </p>
      )}
    </section>
  )
}

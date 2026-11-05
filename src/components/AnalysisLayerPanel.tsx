import { useId, useState } from 'react'
import {
  deaLandCoverProduct,
  landCoverLevel3Classes,
  landCoverYears,
  type LandCoverYear,
} from '../map/deaLandCover.ts'
import {
  findSentinelLayer,
  sentinelViewLabels,
  sentinelViews,
  type SentinelContinuousLayer,
  type SentinelIndexMetadata,
  type SentinelView,
} from '../map/sentinelIndexLayers.ts'

export type AnalysisSource = 'dea' | 'sentinel'

export type AnalysisSelection = {
  isEnabled: boolean
  source: AnalysisSource
  deaYear: LandCoverYear
  sentinelView: SentinelView
}

export type AnalysisDisplayStatus = 'hidden' | 'loading' | 'ready' | 'error' | 'zoomed-out'

export type SentinelMetadataStatus = 'loading' | 'ready' | 'unavailable'

type AnalysisLayerPanelProps = {
  isMapReady: boolean
  selection: AnalysisSelection
  opacity: number
  isDisplaySmoothed: boolean
  status: AnalysisDisplayStatus
  sentinelMetadata: SentinelIndexMetadata | null
  sentinelMetadataStatus: SentinelMetadataStatus
  onToggle: () => void
  onSelectSource: (source: AnalysisSource) => void
  onSelectDeaYear: (year: LandCoverYear) => void
  onSelectSentinelView: (view: SentinelView) => void
  onChangeOpacity: (opacity: number) => void
  onToggleDisplaySmoothing: () => void
  onRetry: () => void
}

type LegendClass = {
  value: number
  name: string
  color: string
}

const roomyScreenQuery = '(min-width: 640px) and (min-height: 640px)'

function isScreenRoomyEnoughForLegend() {
  return window.matchMedia(roomyScreenQuery).matches
}

function formatDate(isoDate: string) {
  return new Date(`${isoDate}T00:00:00Z`).toLocaleDateString('en-AU', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    timeZone: 'UTC',
  })
}

function formatIndexValue(value: number) {
  return value.toFixed(1).replace('-', '−')
}

function selectedLayerName(selection: AnalysisSelection, sentinelMetadata: SentinelIndexMetadata | null) {
  if (selection.source === 'dea') {
    return `DEA land cover ${selection.deaYear}`
  }
  const title = sentinelMetadata ? findSentinelLayer(sentinelMetadata, selection.sentinelView).title : 'Sentinel-2'
  return `${title} 2025`
}

function CategoricalLegend({ label, classes }: { label: string; classes: readonly LegendClass[] }) {
  return (
    <ul className="analysis-legend" aria-label={label}>
      {classes.map((legendClass) => (
        <li key={legendClass.value} className="analysis-legend-item">
          <span
            className="analysis-swatch"
            style={{ backgroundColor: legendClass.color }}
            aria-hidden="true"
          />
          {legendClass.name}
        </li>
      ))}
    </ul>
  )
}

function ContinuousLegend({ layer }: { layer: SentinelContinuousLayer }) {
  const [minimum, maximum] = layer.range
  const gradient = layer.stops
    .map(([value, color]) => `${color} ${(((value - minimum) / (maximum - minimum)) * 100).toFixed(1)}%`)
    .join(', ')
  const tickValues = [minimum, ...(minimum < 0 && maximum > 0 ? [0] : []), maximum]

  return (
    <figure className="analysis-gradient" aria-label={`${layer.title} colour scale from ${minimum} to ${maximum}`}>
      <div className="analysis-gradient-bar" style={{ backgroundImage: `linear-gradient(to right, ${gradient})` }} />
      <div className="analysis-gradient-ticks" aria-hidden="true">
        {tickValues.map((value) => (
          <span
            key={value}
            className="analysis-gradient-tick"
            style={{ left: `${((value - minimum) / (maximum - minimum)) * 100}%` }}
          >
            {formatIndexValue(value)}
          </span>
        ))}
      </div>
      <figcaption className="analysis-note">
        {layer.title} = {layer.formula}. Shown in {layer.steps} colour steps; values beyond the scale use its end
        colours.
      </figcaption>
    </figure>
  )
}

function DeaDetails() {
  return (
    <>
      <CategoricalLegend label="DEA Level 3 land cover classes" classes={landCoverLevel3Classes} />
      <p className="analysis-note">Pixels with no data are left transparent.</p>
      <p className="analysis-note">
        Published classifications by Digital Earth Australia:{' '}
        <a href={deaLandCoverProduct.productPageUrl} target="_blank" rel="noopener">
          {deaLandCoverProduct.name}
        </a>{' '}
        {deaLandCoverProduct.classificationLevel}, version {deaLandCoverProduct.version}, ©{' '}
        {deaLandCoverProduct.copyrightHolder},{' '}
        <a href={deaLandCoverProduct.licenceUrl} target="_blank" rel="noopener">
          {deaLandCoverProduct.licenceName}
        </a>
        . Each year summarises January to December Landsat observations at {deaLandCoverProduct.resolutionMetres} m.
      </p>
      <p className="analysis-note">
        The DEA layer covers all of Australia, so colours continue past the Gold Coast boundary and up to about 130 km
        out to sea, where the sea is mapped as Water. DEA advises against using its classes over the ocean.
      </p>
    </>
  )
}

function SentinelDetails({ metadata, view }: { metadata: SentinelIndexMetadata; view: SentinelView }) {
  const layer = findSentinelLayer(metadata, view)

  return (
    <>
      {layer.kind === 'categorical' ? (
        <CategoricalLegend label="Index rule classes" classes={layer.classes} />
      ) : (
        <ContinuousLegend layer={layer} />
      )}
      {layer.kind === 'categorical' ? (
        <p className="analysis-note">
          Classes come from a simple threshold rule on NDVI, NDBI and MNDWI. Candidate artificial surface is a
          screening result, not verified land cover, and bare soil or sand can fall into it or into Uncertain. Grey
          marks pixels with fewer than {metadata.minimum_valid_observations} clear observations in 2025.
        </p>
      ) : null}
      <p className="analysis-note">
        Transparent: outside the Gold Coast boundary
        {layer.kind === 'continuous' ? ` or fewer than ${metadata.minimum_valid_observations} clear observations` : ''}.
      </p>
      <p className="analysis-note">
        This project's analysis, not a DEA product: {metadata.source.product} from{' '}
        <a href={metadata.source.stac_collection} target="_blank" rel="noopener">
          Earth Search
        </a>
        , {metadata.acquisitions_used} acquisitions from {formatDate(metadata.period.first_acquisition)} to{' '}
        {formatDate(metadata.period.last_acquisition)}. Clouds, shadows and invalid pixels are masked with the scene
        classification layer, each index is calculated per acquisition, and the annual median is taken on a{' '}
        {metadata.resolution_m} m grid. {metadata.source.attribution}.
      </p>
    </>
  )
}

export function AnalysisLayerPanel({
  isMapReady,
  selection,
  opacity,
  isDisplaySmoothed,
  status,
  sentinelMetadata,
  sentinelMetadataStatus,
  onToggle,
  onSelectSource,
  onSelectDeaYear,
  onSelectSentinelView,
  onChangeOpacity,
  onToggleDisplaySmoothing,
  onRetry,
}: AnalysisLayerPanelProps) {
  const [isLegendOpen, setIsLegendOpen] = useState(isScreenRoomyEnoughForLegend)
  const headingId = useId()
  const sourceGroupName = useId()
  const optionGroupName = useId()
  const opacityInputId = useId()
  const smoothingNoteId = useId()
  const detailsId = useId()
  const opacityPercent = Math.round(opacity * 100)
  const areLayerSettingsDisabled = !isMapReady || !selection.isEnabled
  const isSentinelAvailable = sentinelMetadataStatus === 'ready' && sentinelMetadata !== null
  const layerName = selectedLayerName(selection, sentinelMetadata)
  const caption =
    selection.source === 'dea'
      ? `${selection.deaYear} · DEA Level 3 · ${deaLandCoverProduct.resolutionMetres} m pixels`
      : `${layerName} · annual median · ${sentinelMetadata?.resolution_m ?? 20} m pixels`

  return (
    <section className="analysis-panel" aria-labelledby={headingId}>
      <div className="analysis-header">
        <h2 id={headingId} className="analysis-title">
          Analysis layer
        </h2>
        <button
          type="button"
          className="switch-toggle analysis-toggle"
          aria-pressed={selection.isEnabled}
          onClick={onToggle}
          disabled={!isMapReady}
        >
          <span className="switch-toggle-track" aria-hidden="true" />
          Show<span className="visually-hidden"> analysis layer</span>
        </button>
      </div>

      <fieldset className="analysis-group" disabled={areLayerSettingsDisabled}>
        <legend className="analysis-label">Source</legend>
        <div className="source-options">
          <label className="source-option">
            <input
              type="radio"
              name={sourceGroupName}
              value="dea"
              checked={selection.source === 'dea'}
              onChange={() => onSelectSource('dea')}
            />
            <span>
              DEA Land Cover <span className="source-option-detail">published, 30 m</span>
            </span>
          </label>
          <label className="source-option">
            <input
              type="radio"
              name={sourceGroupName}
              value="sentinel"
              checked={selection.source === 'sentinel'}
              onChange={() => onSelectSource('sentinel')}
              disabled={!isSentinelAvailable}
            />
            <span>
              Sentinel-2 indices <span className="source-option-detail">this project, 20 m</span>
            </span>
          </label>
        </div>
        {sentinelMetadataStatus === 'unavailable' && (
          <p className="analysis-note">The Sentinel-2 outputs could not be loaded.</p>
        )}
      </fieldset>

      <fieldset className="analysis-group" disabled={areLayerSettingsDisabled}>
        <legend className="analysis-label">{selection.source === 'dea' ? 'Year' : 'View (2025)'}</legend>
        {selection.source === 'dea' ? (
          <div className="segmented-control" style={{ gridTemplateColumns: `repeat(${landCoverYears.length}, 1fr)` }}>
            {landCoverYears.map((optionYear) => (
              <label key={optionYear} className="segmented-option">
                <input
                  type="radio"
                  name={optionGroupName}
                  value={optionYear}
                  checked={optionYear === selection.deaYear}
                  onChange={() => onSelectDeaYear(optionYear)}
                />
                <span>{optionYear}</span>
              </label>
            ))}
          </div>
        ) : (
          <div className="segmented-control" style={{ gridTemplateColumns: `repeat(${sentinelViews.length}, 1fr)` }}>
            {sentinelViews.map((view) => (
              <label key={view} className="segmented-option">
                <input
                  type="radio"
                  name={optionGroupName}
                  value={view}
                  checked={view === selection.sentinelView}
                  onChange={() => onSelectSentinelView(view)}
                />
                <span>{sentinelViewLabels[view]}</span>
              </label>
            ))}
          </div>
        )}
      </fieldset>

      <div className="analysis-opacity">
        <label htmlFor={opacityInputId} className="analysis-label">
          Opacity
        </label>
        <input
          id={opacityInputId}
          type="range"
          min={0}
          max={100}
          step={5}
          value={opacityPercent}
          aria-valuetext={`${opacityPercent}%`}
          onChange={(event) => onChangeOpacity(Number(event.currentTarget.value) / 100)}
          disabled={areLayerSettingsDisabled}
        />
        <output htmlFor={opacityInputId} className="analysis-opacity-value">
          {opacityPercent}%
        </output>
      </div>

      <div className="analysis-smoothing">
        <button
          type="button"
          className="switch-toggle analysis-toggle smoothing-toggle"
          aria-pressed={isDisplaySmoothed}
          aria-describedby={smoothingNoteId}
          onClick={onToggleDisplaySmoothing}
          disabled={areLayerSettingsDisabled}
        >
          <span className="switch-toggle-track" aria-hidden="true" />
          Smooth display
        </button>
        <p id={smoothingNoteId} className="analysis-note smoothing-note">
          Smoothing blends neighbouring pixel colours on screen only. Blended colours are not extra classes or values.
          Switch it off to see each pixel exactly.
        </p>
      </div>

      <p className="analysis-caption">{caption}</p>

      <div className="analysis-status" role="status">
        {status === 'loading' && <p>Loading {layerName}…</p>}
        {status === 'zoomed-out' && <p>Zoom in to see this layer.</p>}
        {status === 'hidden' && <p>The analysis layer is hidden.</p>}
      </div>

      {status === 'error' && (
        <div className="analysis-error" role="alert">
          <p>Some {layerName} tiles could not be loaded. The rest of the map still works.</p>
          <button type="button" className="analysis-retry" onClick={onRetry}>
            Try again
          </button>
        </div>
      )}

      <button
        type="button"
        className="analysis-disclosure"
        aria-expanded={isLegendOpen}
        aria-controls={detailsId}
        onClick={() => setIsLegendOpen((isOpen) => !isOpen)}
      >
        Legend and source
      </button>

      <div id={detailsId} className="analysis-details" hidden={!isLegendOpen}>
        {selection.source === 'sentinel' && sentinelMetadata ? (
          <SentinelDetails metadata={sentinelMetadata} view={selection.sentinelView} />
        ) : (
          <DeaDetails />
        )}
      </div>
    </section>
  )
}

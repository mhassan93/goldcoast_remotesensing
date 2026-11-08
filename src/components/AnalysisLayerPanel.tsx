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
  sentinelYears,
  type SentinelContinuousLayer,
  type SentinelIndexMetadata,
  type SentinelMetadataByYear,
  type SentinelView,
  type SentinelYear,
} from '../map/sentinelIndexLayers.ts'

export type AnalysisSource = 'dea' | 'sentinel'

export type AnalysisSelection = {
  isEnabled: boolean
  source: AnalysisSource
  deaYear: LandCoverYear
  sentinelYear: SentinelYear
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
  sentinelMetadata: SentinelMetadataByYear
  sentinelMetadataStatus: SentinelMetadataStatus
  onToggle: () => void
  onSelectSource: (source: AnalysisSource) => void
  onSelectDeaYear: (year: LandCoverYear) => void
  onSelectSentinelYear: (year: SentinelYear) => void
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

function formatAcquisitionPeriod(firstIsoDate: string, lastIsoDate: string) {
  const first = formatDate(firstIsoDate)
  const last = formatDate(lastIsoDate)
  const sameYear = firstIsoDate.slice(0, 4) === lastIsoDate.slice(0, 4)
  return `${sameYear ? first.replace(/ \d{4}$/, '') : first} – ${last}`
}

function formatIndexValue(value: number) {
  return value.toFixed(1).replace('-', '−')
}

function selectedLayerName(selection: AnalysisSelection, sentinelMetadata: SentinelMetadataByYear) {
  if (selection.source === 'dea') {
    return `DEA land cover ${selection.deaYear}`
  }
  const metadata = sentinelMetadata[selection.sentinelYear]
  const title = metadata ? findSentinelLayer(metadata, selection.sentinelView).title : 'Sentinel-2'
  return `${title} ${selection.sentinelYear}`
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
        Clipped to the Gold Coast boundary by this project from DEA's Level 3 GeoTIFFs. Class codes and colours are
        unchanged.
      </p>
    </>
  )
}

function SentinelDetails({
  metadata,
  year,
  view,
}: {
  metadata: SentinelIndexMetadata
  year: SentinelYear
  view: SentinelView
}) {
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
          marks pixels with fewer than {metadata.minimum_valid_observations} clear observations in {year}.
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
  onSelectSentinelYear,
  onSelectSentinelView,
  onChangeOpacity,
  onToggleDisplaySmoothing,
  onRetry,
}: AnalysisLayerPanelProps) {
  const [isLegendOpen, setIsLegendOpen] = useState(isScreenRoomyEnoughForLegend)
  const headingId = useId()
  const sourceGroupName = useId()
  const yearGroupName = useId()
  const viewGroupName = useId()
  const opacityInputId = useId()
  const smoothingNoteId = useId()
  const detailsId = useId()
  const opacityPercent = Math.round(opacity * 100)
  const areLayerSettingsDisabled = !isMapReady || !selection.isEnabled
  const isSentinelAvailable = sentinelMetadataStatus === 'ready'
  const selectedSentinelMetadata = sentinelMetadata[selection.sentinelYear]
  const layerName = selectedLayerName(selection, sentinelMetadata)
  const caption =
    selection.source === 'dea'
      ? `${selection.deaYear} · DEA Level 3 · ${deaLandCoverProduct.resolutionMetres} m pixels`
      : selectedSentinelMetadata
        ? `${layerName} · median of ${formatAcquisitionPeriod(
            selectedSentinelMetadata.period.first_acquisition,
            selectedSentinelMetadata.period.last_acquisition,
          )} · ${selectedSentinelMetadata.resolution_m} m pixels`
        : layerName
  const yearOptions: readonly number[] = selection.source === 'dea' ? landCoverYears : sentinelYears
  const selectedYear = selection.source === 'dea' ? selection.deaYear : selection.sentinelYear
  const selectYear = (year: number) => {
    if (selection.source === 'dea') {
      onSelectDeaYear(year as LandCoverYear)
    } else {
      onSelectSentinelYear(year as SentinelYear)
    }
  }

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
        <legend className="analysis-label">Year</legend>
        <div className="segmented-control" style={{ gridTemplateColumns: `repeat(${yearOptions.length}, 1fr)` }}>
          {yearOptions.map((optionYear) => (
            <label key={`${selection.source}-${optionYear}`} className="segmented-option">
              <input
                type="radio"
                name={yearGroupName}
                value={optionYear}
                checked={optionYear === selectedYear}
                onChange={() => selectYear(optionYear)}
                disabled={selection.source === 'sentinel' && !sentinelMetadata[optionYear as SentinelYear]}
              />
              <span>{optionYear}</span>
            </label>
          ))}
        </div>
      </fieldset>

      {selection.source === 'sentinel' && (
        <fieldset className="analysis-group" disabled={areLayerSettingsDisabled}>
          <legend className="analysis-label">View</legend>
          <div className="segmented-control" style={{ gridTemplateColumns: `repeat(${sentinelViews.length}, 1fr)` }}>
            {sentinelViews.map((view) => (
              <label key={view} className="segmented-option">
                <input
                  type="radio"
                  name={viewGroupName}
                  value={view}
                  checked={view === selection.sentinelView}
                  onChange={() => onSelectSentinelView(view)}
                />
                <span>{sentinelViewLabels[view]}</span>
              </label>
            ))}
          </div>
        </fieldset>
      )}

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

      {selection.source === 'dea' && (
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
      )}

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
        {selection.source === 'sentinel' && selectedSentinelMetadata ? (
          <SentinelDetails
            metadata={selectedSentinelMetadata}
            year={selection.sentinelYear}
            view={selection.sentinelView}
          />
        ) : (
          <DeaDetails />
        )}
      </div>
    </section>
  )
}

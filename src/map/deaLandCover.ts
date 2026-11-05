export const landCoverYears = [2010, 2025] as const

export type LandCoverYear = (typeof landCoverYears)[number]

export const defaultLandCoverYear: LandCoverYear = 2025

export type LandCoverClass = {
  value: number
  name: string
  color: string
}

export const landCoverLevel3Classes: readonly LandCoverClass[] = [
  { value: 111, name: 'Cultivated Terrestrial Vegetation', color: '#acbc2d' },
  { value: 112, name: '(Semi-)Natural Terrestrial Vegetation', color: '#0e7912' },
  { value: 124, name: 'Natural Aquatic Vegetation', color: '#1ebf79' },
  { value: 215, name: 'Artificial Surface', color: '#da5c69' },
  { value: 216, name: 'Natural Bare Surface', color: '#f3ab69' },
  { value: 220, name: 'Water', color: '#4d9fdc' },
]

export const deaLandCoverProduct = {
  name: 'DEA Land Cover (Landsat)',
  classificationLevel: 'Level 3',
  version: '2.0.0',
  resolutionMetres: 30,
  productPageUrl: 'https://knowledge.dea.ga.gov.au/data/product/dea-land-cover-landsat/',
  licenceName: 'CC BY 4.0',
  licenceUrl: 'https://creativecommons.org/licenses/by/4.0/',
  copyrightHolder: 'Commonwealth of Australia (Geoscience Australia)',
}

export const deaLandCoverAttribution = `Land cover: <a href="${deaLandCoverProduct.productPageUrl}" target="_blank" rel="noopener">DEA Land Cover v${deaLandCoverProduct.version}</a> © ${deaLandCoverProduct.copyrightHolder}, <a href="${deaLandCoverProduct.licenceUrl}" target="_blank" rel="noopener">${deaLandCoverProduct.licenceName}</a>`

const deaWmtsUrl = 'https://ows.dea.ga.gov.au/wmts'
const deaLandCoverServiceLayer = 'ga_ls_landcover_c3'
const deaLandCoverLevel3Style = 'level3'
const webMercatorTileMatrixSet = 'WholeWorld_WebMercator'

export const deaLandCoverTileSize = 256
export const deaLandCoverMinZoom = 7
export const deaLandCoverMaxZoom = 14
export const deaLandCoverBounds: [number, number, number, number] = [
  112.343354889631, -44.3403132062909, 155.073704691127, -9.40358670690844,
]

export function deaLandCoverTimeValue(year: LandCoverYear) {
  return `${year}-01-01`
}

export function deaLandCoverTileUrl(year: LandCoverYear) {
  const query = new URLSearchParams({
    service: 'WMTS',
    request: 'GetTile',
    version: '1.0.0',
    layer: deaLandCoverServiceLayer,
    style: deaLandCoverLevel3Style,
    format: 'image/png',
    tileMatrixSet: webMercatorTileMatrixSet,
    Time: deaLandCoverTimeValue(year),
  })
  return `${deaWmtsUrl}?${query.toString()}&tileMatrix={z}&tileCol={x}&tileRow={y}`
}

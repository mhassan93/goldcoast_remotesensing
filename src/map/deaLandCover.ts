import { publicDataTileUrl } from './publicData.ts'

export const landCoverYears = [2010, 2015, 2020, 2025] as const

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

export const deaLandCoverAttribution = `Land cover: <a href="${deaLandCoverProduct.productPageUrl}" target="_blank" rel="noopener">DEA Land Cover v${deaLandCoverProduct.version}</a> © ${deaLandCoverProduct.copyrightHolder}, <a href="${deaLandCoverProduct.licenceUrl}" target="_blank" rel="noopener">${deaLandCoverProduct.licenceName}</a>, clipped to the study area`

export const deaLandCoverTileSize = 256
export const deaLandCoverMinZoom = 7
export const deaLandCoverMaxZoom = 14
export const deaLandCoverBounds: [number, number, number, number] = [
  153.168916182, -28.26511344, 153.551945912, -27.690382825,
]

export function deaLandCoverTileUrl(year: LandCoverYear) {
  return publicDataTileUrl(`dea-land-cover/${year}/{z}/{x}/{y}.png`)
}

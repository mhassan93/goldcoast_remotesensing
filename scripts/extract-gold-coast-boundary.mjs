import { mkdir, writeFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const localGovernmentLayerQueryUrl =
  'https://spatial-gis.information.qld.gov.au/arcgis/rest/services/Boundaries/AdministrativeBoundaries/MapServer/1/query'
const goldCoastLgaCode = '3430'
const gda2020GeographicWkid = 7844
const coordinateDecimalPlaces = 9
const outputPath = resolve(
  dirname(fileURLToPath(import.meta.url)),
  '../public/data/gold-coast-boundary.geojson',
)

const queryParameters = new URLSearchParams({
  where: `lga_code='${goldCoastLgaCode}'`,
  outFields: 'lga,abbrev_name,lga_code,ca_area_sqkm',
  returnGeometry: 'true',
  outSR: String(gda2020GeographicWkid),
  f: 'geojson',
})

const response = await fetch(`${localGovernmentLayerQueryUrl}?${queryParameters}`)
if (!response.ok) {
  throw new Error(`Boundary service request failed with HTTP ${response.status}`)
}

const sourceCollection = await response.json()
if (sourceCollection.exceededTransferLimit) {
  throw new Error('Boundary service reported that the transfer limit was exceeded')
}
if (sourceCollection.features?.length !== 1) {
  throw new Error(`Expected one Gold Coast feature, received ${sourceCollection.features?.length}`)
}

const [sourceFeature] = sourceCollection.features
const sourceGeometry = sourceFeature.geometry
if (sourceGeometry.type !== 'Polygon' && sourceGeometry.type !== 'MultiPolygon') {
  throw new Error(`Unexpected geometry type ${sourceGeometry.type}`)
}

const sourcePolygons =
  sourceGeometry.type === 'Polygon' ? [sourceGeometry.coordinates] : sourceGeometry.coordinates

const roundCoordinate = (value) => Number(value.toFixed(coordinateDecimalPlaces))

const calculateSignedRingArea = (ring) => {
  let doubledArea = 0
  for (let index = 0; index < ring.length - 1; index += 1) {
    const [currentLongitude, currentLatitude] = ring[index]
    const [nextLongitude, nextLatitude] = ring[index + 1]
    doubledArea += currentLongitude * nextLatitude - nextLongitude * currentLatitude
  }
  return doubledArea / 2
}

const applyRightHandRule = (ring, ringIndex) => {
  const isOuterRing = ringIndex === 0
  const isCounterClockwise = calculateSignedRingArea(ring) > 0
  return isOuterRing === isCounterClockwise ? ring : [...ring].reverse()
}

let largestRoundingShift = 0
let reversedRingCount = 0

const outputPolygons = sourcePolygons.map((polygon) =>
  polygon.map((sourceRing, ringIndex) => {
    const roundedRing = sourceRing.map((position) =>
      position.map((value) => {
        const roundedValue = roundCoordinate(value)
        largestRoundingShift = Math.max(largestRoundingShift, Math.abs(roundedValue - value))
        return roundedValue
      }),
    )
    const orientedRing = applyRightHandRule(roundedRing, ringIndex)
    if (orientedRing !== roundedRing) {
      reversedRingCount += 1
    }
    return orientedRing
  }),
)

const isSamePosition = (first, second) => first[0] === second[0] && first[1] === second[1]

for (const [polygonIndex, polygon] of outputPolygons.entries()) {
  if (polygon.length !== sourcePolygons[polygonIndex].length) {
    throw new Error(`Polygon ${polygonIndex} lost rings during conversion`)
  }
  for (const [ringIndex, ring] of polygon.entries()) {
    if (ring.length !== sourcePolygons[polygonIndex][ringIndex].length) {
      throw new Error(`Ring ${ringIndex} of polygon ${polygonIndex} changed vertex count`)
    }
    if (!isSamePosition(ring[0], ring[ring.length - 1])) {
      throw new Error(`Ring ${ringIndex} of polygon ${polygonIndex} is not closed`)
    }
    for (let index = 1; index < ring.length; index += 1) {
      if (isSamePosition(ring[index - 1], ring[index])) {
        throw new Error(`Rounding produced a repeated vertex in ring ${ringIndex} of polygon ${polygonIndex}`)
      }
    }
  }
}

const outputCollection = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      properties: {
        lga: sourceFeature.properties.lga,
        abbrev_name: sourceFeature.properties.abbrev_name,
        lga_code: sourceFeature.properties.lga_code,
        ca_area_sqkm: sourceFeature.properties.ca_area_sqkm,
      },
      geometry: {
        type: sourceGeometry.type,
        coordinates: sourceGeometry.type === 'Polygon' ? outputPolygons[0] : outputPolygons,
      },
    },
  ],
}

const allPositions = outputPolygons.flat(2)
const longitudes = allPositions.map(([longitude]) => longitude)
const latitudes = allPositions.map(([, latitude]) => latitude)
const outputText = `${JSON.stringify(outputCollection)}\n`

await mkdir(dirname(outputPath), { recursive: true })
await writeFile(outputPath, outputText, 'utf8')

console.log(`Feature: ${sourceFeature.properties.lga} (LGA code ${sourceFeature.properties.lga_code})`)
console.log(`Geometry type: ${sourceGeometry.type}`)
console.log(`Polygons: ${outputPolygons.length}`)
console.log(`Rings per polygon: ${outputPolygons.map((polygon) => polygon.length).join(', ')}`)
console.log(`Vertices: ${allPositions.length}`)
console.log(`Rings reversed for RFC 7946 winding: ${reversedRingCount}`)
console.log(`Largest coordinate change from rounding: ${largestRoundingShift.toExponential(2)} degrees`)
console.log(
  `Extent: ${Math.min(...longitudes)}, ${Math.min(...latitudes)}, ${Math.max(...longitudes)}, ${Math.max(...latitudes)}`,
)
console.log(`Wrote ${Buffer.byteLength(outputText)} bytes to ${outputPath}`)

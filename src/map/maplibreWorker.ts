import { setWorkerUrl } from 'maplibre-gl'
import maplibreWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url'

export function configureMapLibreWorker() {
  setWorkerUrl(maplibreWorkerUrl)
}

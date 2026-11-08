export const publicDataUrl = `${import.meta.env.BASE_URL}data/`

export function publicDataTileUrl(path: string) {
  return new URL(`${publicDataUrl}${path}`, window.location.href).href
    .replace('%7Bz%7D', '{z}')
    .replace('%7Bx%7D', '{x}')
    .replace('%7By%7D', '{y}')
}

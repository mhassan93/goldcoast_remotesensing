import react from '@vitejs/plugin-react'
import { defineConfig, type Plugin } from 'vite'

const pagesBasePath = process.env.PAGES_BASE_PATH ?? ''

const mapServiceOrigins = ['https://tiles.openfreemap.org', 'https://tiles.mapterhorn.com']

const productionContentSecurityPolicy = [
  "default-src 'self'",
  "script-src 'self'",
  "style-src 'self'",
  "img-src 'self' data: blob:",
  "font-src 'self'",
  `connect-src 'self' ${mapServiceOrigins.join(' ')}`,
  "worker-src 'self' blob:",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'none'",
].join('; ')

function contentSecurityPolicyForBuild(): Plugin {
  return {
    name: 'content-security-policy-for-build',
    apply: 'build',
    transformIndexHtml: () => [
      {
        tag: 'meta',
        attrs: { 'http-equiv': 'Content-Security-Policy', content: productionContentSecurityPolicy },
        injectTo: 'head-prepend',
      },
    ],
  }
}

export default defineConfig({
  base: `${pagesBasePath.replace(/\/+$/, '')}/`,
  plugins: [react(), contentSecurityPolicyForBuild()],
  build: {
    license: { fileName: 'third-party-licenses.txt' },
  },
})

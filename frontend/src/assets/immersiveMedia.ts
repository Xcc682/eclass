// H5 bundles every authored scene automatically. Adding a generated branch
// atlas no longer requires editing a long manual import table.
const media: Record<string, string> = {}

// #ifdef H5
const bundledMedia = import.meta.glob<string>('./immersive/*.{webp,png,jpg,jpeg}', {
  eager: true,
  query: '?url',
  import: 'default',
})

Object.entries(bundledMedia).forEach(([path, url]) => {
  const filename = path.split('/').pop()
  if (filename) media[filename] = url
})
// #endif

export function resolveImmersiveMedia(value?: string): string {
  if (!value) return ''
  const rawFilename = value.split('/').pop() || value
  const filename = rawFilename.split(/[?#]/, 1)[0]
  if (media[filename]) return media[filename]
  const base = (import.meta.env.VITE_MEDIA_BASE_URL || 'http://127.0.0.1:8000/media/immersive').replace(/\/$/, '')
  return `${base}/images/${filename}`
}

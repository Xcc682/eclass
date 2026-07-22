// Vite plugin: convert rpx → rem (responsive)
// Based on: 100rpx = 1rem, root font-size = min(100vw, 480px) / 7.5
// On phone: 375px screen → 100rpx = 50px, 480px → 100rpx = 64px

export function rpxPlugin() {
  return {
    name: 'vite-plugin-rpx-to-rem',
    enforce: 'pre' as const,
    transform(code: string, id: string) {
      if (id.endsWith('.vue') || id.endsWith('.scss') || id.endsWith('.css')) {
        const transformed = code.replace(/(\d+(?:\.\d+)?)rpx/g, (_: string, num: string) => {
          const remValue = (parseFloat(num) / 100).toFixed(4)
          return remValue + 'rem'
        })
        return { code: transformed, map: null }
      }
    }
  }
}

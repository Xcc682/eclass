import { defineConfig } from 'vite'
import uni from '@dcloudio/vite-plugin-uni'
import path from 'path'
import { rpxPlugin } from './src/utils/rpx-plugin'

export default defineConfig(() => {
  const aliases: Record<string, string> = { '@': '/src' }
  // The lifecycle shim exists only for the custom Vue Router H5 shell.  It
  // must never replace the real uni-app runtime in a mini-program build.
  if (!process.env.UNI_PLATFORM || process.env.UNI_PLATFORM === 'h5') {
    aliases['@dcloudio/uni-app'] = path.resolve(__dirname, 'src/shims/uni-app.ts')
  }

  return {
    plugins: [rpxPlugin(), uni()],
    resolve: { alias: aliases },
    server: {
      host: '0.0.0.0',
      port: 5667,
      proxy: {
        '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true }
      }
    }
  }
})

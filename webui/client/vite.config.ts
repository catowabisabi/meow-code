import { defineConfig, createLogger } from 'vite'
import react from '@vitejs/plugin-react'

// 自定義 logger：過濾 ws proxy socket error，改為簡短中文提示
const logger = createLogger()
const originalError = logger.error.bind(logger)
logger.error = (msg, options) => {
  if (msg.includes('ws proxy socket error')) {
    logger.warn('⚠️ 後端 WebSocket 未就緒，前端會自動重連...')
    return
  }
  originalError(msg, options)
}

export default defineConfig({
  plugins: [react()],
  customLogger: logger,
  server: {
    port: 7777,
    proxy: {
      '/api': {
        target: 'http://localhost:7778',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:7778',
        ws: true,
        configure: (proxy) => {
          proxy.on('error', () => {})
          proxy.on('proxyReqWs', (_proxyReq: unknown, _req: unknown, socket: any) => {
            socket.on('error', () => {})
          })
        },
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
})

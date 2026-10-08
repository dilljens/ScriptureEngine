import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    // NOTE: 5175 is held by axe-viewer's sticky lease (running with
    // --strictPort). Pinned to 5176 so a silent auto-bump never lands on a
    // port the chat origin allowlist rejects (web/routes/chat.py).
    port: 5176,
    strictPort: true,
    proxy: {
      '/api/memorize': {
        target: 'http://localhost:8090',
        changeOrigin: true,
      },
      '/api': {
        target: 'http://localhost:5174',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    rollupOptions: {
      output: {
        // Perf (Track C1): cytoscape (~350KB, graph tabs only) and the
        // markdown stack (5 importing components) load on demand instead
        // of riding the initial chunks.
        manualChunks: {
          cytoscape: ['cytoscape'],
          markdown: ['react-markdown', 'remark-gfm', 'rehype-raw'],
        },
      },
    },
  },
})

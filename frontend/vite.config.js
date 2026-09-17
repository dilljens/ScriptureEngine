import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5175,
    proxy: {
      '/api/memorize': {
        target: 'http://localhost:8090',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/memorize/, ''),
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

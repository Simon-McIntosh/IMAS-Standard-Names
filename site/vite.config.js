import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Vite config for the IMAS Standard Names Catalog SPA.
//
// `base: './'` produces relative URLs in the build output so the bundle
// can be served from any subdirectory (e.g. mike-style versioned paths
// like `/v0.1.0/`) and even opens correctly from a file:// URL.
//
// `data.json` is loaded at runtime via `fetch('./data.json')` rather than
// imported, so the SPA build is independent of the dataset and a single
// build can be deployed against many dataset revisions.
export default defineConfig({
  plugins: [react()],
  base: './',
  build: {
    sourcemap: true,
    outDir: 'dist',
    target: 'es2020',
    rollupOptions: {
      output: {
        manualChunks(id) {
          // Vendor split so KaTeX and the lazy Mermaid chunk stay separate.
          if (id.includes('node_modules/katex')) return 'vendor-katex';
          if (id.includes('node_modules/mermaid')) return 'vendor-mermaid';
          if (id.includes('node_modules/react') || id.includes('node_modules/react-dom')) {
            return 'vendor-react';
          }
          return undefined;
        },
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./tests/setup.js'],
    css: false,
  },
});

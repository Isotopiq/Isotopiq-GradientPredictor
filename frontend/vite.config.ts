/// <reference types="vitest" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { nodePolyfills } from 'vite-plugin-node-polyfills';
import { fileURLToPath, URL } from 'node:url';

export default defineConfig({
  plugins: [
    react(),
    nodePolyfills({
      // Polyfill Node.js built-ins (util, buffer, events, etc.) needed by ketcher-standalone
      include: ['events', 'util', 'buffer', 'stream', 'path', 'crypto'],
      globals: {
        Buffer: true,
        global: true,
        process: true,
      },
    }),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 18717,
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:18700',
        changeOrigin: true,
      },
    },
  },
  optimizeDeps: {
    include: ['ketcher-react', 'ketcher-standalone'],
    exclude: ['ketcher-standalone/dist/binaryWasm'],
  },
  build: {
    chunkSizeWarningLimit: 1500,
    rollupOptions: {
      output: {
        manualChunks: {
          ketcher: ['ketcher-react', 'ketcher-standalone'],
        },
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './tests/setup.ts',
    css: true,
  },
});

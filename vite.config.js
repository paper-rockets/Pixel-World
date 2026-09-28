import { defineConfig } from 'vite';

export default defineConfig({
  base: './', // so the built game works from any folder or web address
  server: { port: 8180, strictPort: true, host: true, allowedHosts: true },
  build: {
    chunkSizeWarningLimit: 2000,
    // two islands, two pages: Lost Ducklings (index.html) and Orange Garden (school.html)
    rolldownOptions: { input: { main: 'index.html', school: 'school.html' } },
  },
});

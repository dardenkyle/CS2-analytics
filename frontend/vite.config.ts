import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// GitHub Pages serves the app as a project page under /CS2-analytics/,
// so built asset URLs must be prefixed with that path.
// https://vite.dev/config/
export default defineConfig({
  base: '/CS2-analytics/',
  plugins: [react()],
})

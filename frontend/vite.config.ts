import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// GitHub Pages serves the app as a project page under /CS2-analytics/, so
// production builds prefix asset URLs with that path. The dev server stays
// at / so local development matches the README URL.
// https://vite.dev/config/
export default defineConfig(({ command }) => ({
  base: command === 'build' ? '/CS2-analytics/' : '/',
  plugins: [react()],
}))

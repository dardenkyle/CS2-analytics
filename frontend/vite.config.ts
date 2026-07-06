import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// GitHub Pages serves the app as a project page under /CS2-analytics/, so
// production builds prefix asset URLs with that path. vite preview serves
// the built output and must use the same base (its command is 'serve', so
// isPreview is the discriminator). Only the dev server stays at / to match
// the README URL.
// https://vite.dev/config/
export default defineConfig(({ command, isPreview }) => ({
  base: command === 'build' || isPreview ? '/CS2-analytics/' : '/',
  plugins: [react()],
}))

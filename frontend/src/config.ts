const DEFAULT_API_BASE_URL = 'https://cs2-analytics.onrender.com'

/**
 * Base URL for the CS2 Analytics API.
 *
 * This is a public URL (it ships in the built bundle either way), so the
 * default lives here in code and no .env file is committed. Override it with
 * VITE_API_BASE_URL at build time, for example in frontend/.env.local
 * (gitignored) to point at a locally running API:
 *
 *   VITE_API_BASE_URL=http://localhost:8000
 */
export const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL

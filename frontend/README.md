# CS2 Analytics Frontend

Public React SPA for CS2 Analytics. Introduces the project and shows live
top players data from the Render-hosted API.

Built with React, TypeScript, and Vite. Deployment to GitHub Pages is added
in a later Phase A branch.

## Requirements

- Node.js 24 LTS (or any recent LTS release)

## Configuration

The API base URL defaults to the production Render service in
`src/config.ts`. It is a public URL (Vite bakes it into the built bundle), so
no `.env` file is committed. Override it at build time with
`VITE_API_BASE_URL`, for example in a gitignored `frontend/.env.local`:

```sh
VITE_API_BASE_URL=http://localhost:8000
```

Note on local development against the production API: the browser only
receives responses when the API's CORS allowlist (`API_CORS_ORIGINS` on the
Render service) includes your page origin. If `http://localhost:5173` is not
in that allowlist, the top players call fails with a CORS error in dev even
though the deployed GitHub Pages site works. Either add the localhost origins
to the Render environment variable or run the API locally and use the
override above.

## Development

Install dependencies:

```sh
npm install
```

Run the dev server (defaults to `http://localhost:5173`):

```sh
npm run dev
```

## Verification

Type-check and build the production bundle:

```sh
npm run build
```

Lint:

```sh
npm run lint
```

Preview the production build locally:

```sh
npm run preview
```

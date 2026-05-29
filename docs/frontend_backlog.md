# Frontend Backlog

This document tracks the product-facing frontend roadmap for the public React
SPA. It is intentionally separate from the main backend/data roadmap in
`docs/backlog.md`.

The frontend roadmap uses lettered phases so it does not conflict with the
backend architecture phases. Phase A is the first frontend phase.

---

## Current Frontend Scope

Initial audience:

- the project owner
- potential employers reviewing the project

Initial product goal:

Show a polished public analytics demo that introduces CS2 Analytics and proves
the deployed API can serve current database-backed player data.

Initial constraints:

- the frontend is a React SPA in `frontend/`
- the app is hosted on GitHub Pages
- deployment runs from `main`
- the app is fully public
- the app calls the Render-hosted backend API
- the first visible data surface uses the existing top players API
- deeper analytics, charts, authentication, and extra API surfaces are deferred

---

## Phase A: Public Top Players Demo

Goal:
Create the first public frontend experience: a polished project introduction
and a simple top players list backed by the live Render API.

Status:
Planned.

### Planned work

- [ ] Create the frontend app shell in `frontend/`
- [ ] Add public project introduction content for portfolio review
- [ ] Add a top players data view using the Render-hosted API
- [ ] Add loading, empty, and error states for the API call
- [ ] Add responsive styling for desktop and mobile review
- [ ] Add GitHub Pages deployment from `main`
- [ ] Document how to configure the frontend API base URL
- [ ] Add a lightweight frontend verification path

### Suggested branch sequence

1. [ ] `phasea-frontend-project-shell`
       Create the React SPA foundation in `frontend/` with the first public page
       structure, project introduction, and basic responsive styling.

   Proposed issue:
   **Frontend A1: Create public project shell**

   Suggested labels:
   `phase: A`, `area: frontend`, `type: implementation`,
   `priority: medium`, `risk: medium`

   Acceptance criteria:
   - `frontend/` contains the React SPA foundation
   - the first screen introduces CS2 Analytics clearly
   - the page looks presentable on desktop and mobile
   - no API integration is required in this branch

   Out of scope:
   - GitHub Pages deployment
   - new backend endpoints
   - charts or deeper analytics

2. [ ] `phasea-top-players-api-view`
       Add the first live data surface by calling the existing top players API
       and rendering a simple list of players.

   Proposed issue:
   **Frontend A2: Show top players from the Render API**

   Suggested labels:
   `phase: A`, `area: frontend`, `type: implementation`,
   `priority: medium`, `risk: low`

   Acceptance criteria:
   - the frontend reads the API base URL from configuration
   - the app calls the top players API from the browser
   - top players render in a clean, scannable list
   - loading, empty, and error states are visible and polished
   - failed API calls do not break the page

   Out of scope:
   - authentication
   - pagination
   - sorting/filtering beyond what the API already supports
   - new API endpoints

3. [ ] `phasea-github-pages-deploy`
       Add the GitHub Pages deployment path so the SPA builds and publishes from
       `main`.

   Proposed issue:
   **Frontend A3: Deploy frontend to GitHub Pages from main**

   Suggested labels:
   `phase: A`, `area: frontend`, `type: deployment`,
   `priority: medium`, `risk: medium`

   Acceptance criteria:
   - GitHub Actions builds the SPA from `frontend/`
   - pushes to `main` publish the app to GitHub Pages
   - SPA routing works after page refreshes on GitHub Pages
   - the deployed app uses the configured Render API base URL
   - deployment setup is documented in the existing deployment or workflow docs

   Out of scope:
   - backend deployment changes
   - custom domain setup
   - private previews or environment-specific deployments

4. [ ] `phasea-frontend-demo-polish`
       Polish the first demo so it is portfolio-ready and comfortable for
       potential employers to review quickly.

   Proposed issue:
   **Frontend A4: Polish public demo experience**

   Suggested labels:
   `phase: A`, `area: frontend`, `type: implementation`,
   `priority: low`, `risk: low`

   Acceptance criteria:
   - the page communicates what the project does without long explanations
   - project links and API/demo context are easy to find
   - top players remain the primary data proof point
   - responsive layout is checked at common desktop and mobile widths
   - frontend verification steps are documented

   Out of scope:
   - second analytics view
   - visual charting library
   - authentication
   - backend/API changes

### Phase A exit criteria

- [ ] A public GitHub Pages URL is available
- [ ] The SPA introduces the project and shows top players from the Render API
- [ ] The app handles loading, empty, and error states gracefully
- [ ] The app is usable on desktop and mobile
- [ ] Deployment from `main` is documented and repeatable

---

## Phase B: Frontend Expansion Candidates

Goal:
Decide the next frontend product surface only after Phase A proves the public
demo path.

Status:
Candidate backlog. Do not start until Phase A is complete and the next user
goal is clear.

Suggested phase label:
`phase: B`

### Candidate work

- [ ] Add a match list view if the backend exposes match read APIs
- [ ] Add a player detail view if the backend exposes player detail APIs
- [ ] Add a small data freshness indicator
- [ ] Add basic filters once the API supports them
- [ ] Add project/process notes for portfolio reviewers

### Decision questions before Phase B

- Which second data surface matters most for a portfolio review: matches,
  players, teams, or ingestion status?
- Should the next frontend branch wait for dbt-backed read models?
- Should the frontend stay a small demo, or begin moving toward a fuller public
  analytics product?

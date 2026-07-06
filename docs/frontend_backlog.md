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

- the public frontend target is a React SPA under `frontend/`
- the former Streamlit debug app at `frontend/app.py` was retired in the A1
  project shell branch; the React SPA replaces it
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
In progress. The A1 project shell is complete: the Streamlit debug app is
retired and `frontend/` now contains the React + TypeScript + Vite SPA with
the public introduction page. A2 (top players view) is next.

A1 implementation notes:

- Branch `phasea-frontend-project-shell` landed as three focused commits:
  retire the Streamlit debug app (`f678196`), scaffold the React + TypeScript
  + Vite toolchain (`08b1564`), and add the public introduction landing page
  (`5c7d3dd`).
- The intro page has no API integration; A2 adds the `top_players` call with
  loading, empty, and error states, including cold-start messaging for the
  Render free-tier API wake-up delay.
- Verification for A1 was `npm run build` (includes TypeScript checking),
  `npm run lint` (oxlint), and manual responsive review at 1440px and 390px.
  The commands are documented in `frontend/README.md`.
- The frontend toolchain requires Node.js (24 LTS used for A1).
- The production API already allows the GitHub Pages origin: live checks show
  `access-control-allow-origin: https://dardenkyle.github.io`, so A3 needs no
  backend CORS change.

### Planned work

- [x] Create the frontend app shell in `frontend/`
- [x] Decide how to handle the existing `frontend/app.py` Streamlit debug app
  (retired; the React SPA replaces it)
- [x] Add public project introduction content for portfolio review
- [ ] Add a top players data view using the Render-hosted API
- [ ] Add loading, empty, and error states for the API call
- [x] Add responsive styling for desktop and mobile review
- [x] Add a frontend build and lint CI job for pull requests (#88)
- [ ] Add GitHub Pages deployment from `main`
- [ ] Document how to configure the frontend API base URL
- [x] Add a lightweight frontend verification path
  (`npm run build` and `npm run lint`, documented in `frontend/README.md`)

### Suggested branch sequence

1. [x] `phasea-frontend-project-shell`
       Decide how to handle the existing Streamlit debug app, then create the
       React SPA foundation in `frontend/` with the first public page structure,
       project introduction, and basic responsive styling.

   Proposed issue:
   **Frontend A1: Create public project shell**

   Suggested labels:
   `phase: A`, `area: frontend`, `type: implementation`,
   `priority: medium`, `risk: medium`

   Acceptance criteria:
   - The branch explicitly replaces, moves, or retires the existing
     `frontend/app.py` Streamlit debug app
   - `frontend/` contains the React SPA foundation after that decision
   - the first screen introduces CS2 Analytics clearly
   - the page looks presentable on desktop and mobile
   - no API integration is required in this branch

   Out of scope:
   - GitHub Pages deployment
   - new backend endpoints
   - charts or deeper analytics

2. [x] `phasea-frontend-ci`
       Add a frontend build and lint job to the CI gate before the first
       frontend logic lands, so A2 and later branches merge under automated
       verification. Tracked by issue #88.

   Proposed issue:
   **[Task]: Add frontend build and lint job to CI** (#88)

   Suggested labels:
   `phase: A`, `area: frontend`, `area: tooling`, `type: implementation`,
   `priority: medium`, `risk: medium`

   Acceptance criteria:
   - pull requests touching `frontend/**` run `npm ci`, `npm run build`, and
     `npm run lint`
   - pull requests that do not touch `frontend/**` do not trigger the
     frontend workflow
   - the job fails the PR gate on TypeScript, build, or lint errors
   - `docs/workflow.md` documents the frontend CI gate

   Out of scope:
   - GitHub Pages deployment (A3)
   - frontend unit tests or a test runner
   - changes to the Python CI jobs

3. [ ] `phasea-top-players-api-view`
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

4. [ ] `phasea-github-pages-deploy`
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

   Implementation notes:
   - set the Vite `base` to `/CS2-analytics/` because GitHub Pages serves the
     app as a project page, not from the domain root
   - prefer hash routing (or no router while the app is a single page) so
     refreshes do not 404 on GitHub Pages
   - no backend CORS change is needed; production already allows the
     `https://dardenkyle.github.io` origin

5. [ ] `phasea-frontend-demo-polish`
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

### Related work outside the frontend

Phase A is aimed at employer review, so a few backend-repo presentability
issues are good interleave candidates while frontend branches are in review:
README design decisions (#82), untracking the `.coverage` artifact (#73),
moving manual scripts out of `tests/` (#72), and optionally moving the
non-working demo subsystem off `main` (#81).

Phase A is not gated by the open ingestion work: the high-priority ingestion
bugs (#71, #74) are Phase 4 entry criteria, the blocked cloud runner issue
(#66) stays deferred because local ingestion against the production database
covers demo data refreshes, and the Phase 3.9 tooling issues (#69, #70, #86)
are independent of this track.

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

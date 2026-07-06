import './App.css'
import { API_BASE_URL } from './config'
import { TopPlayersSection } from './components/TopPlayers'

const GITHUB_URL = 'https://github.com/dardenkyle/CS2-analytics'

interface PipelineStage {
  step: string
  title: string
  description: string
}

const PIPELINE_STAGES: PipelineStage[] = [
  {
    step: '01',
    title: 'Discover',
    description:
      'Results discovery scans public match results for completed professional matches and records each one in PostgreSQL-backed ingestion-state tables.',
  },
  {
    step: '02',
    title: 'Ingest',
    description:
      'Match and map stages fetch and parse pages with retry, backoff, and browser-session recovery, tracking every item through an explicit lifecycle.',
  },
  {
    step: '03',
    title: 'Store',
    description:
      'Parsed match, map, and player statistics are upserted idempotently into PostgreSQL through an Alembic-managed schema.',
  },
  {
    step: '04',
    title: 'Serve',
    description:
      'A FastAPI service deployed on Render exposes player analytics from the live database over a public REST API.',
  },
  {
    step: '05',
    title: 'Present',
    description:
      'This site is the public face of the system. The top players table above is fetched live from the production database through that API.',
  },
]

interface Highlight {
  title: string
  description: string
}

const HIGHLIGHTS: Highlight[] = [
  {
    title: 'Lifecycle-driven ingestion',
    description:
      'Every match and map moves through explicit ingestion-state tables, so scraping runs are resumable, idempotent, and observable instead of fire-and-forget.',
  },
  {
    title: 'Layered architecture',
    description:
      'Controllers own batch coordination, stage services own per-item workflow, and scrapers, parsers, and storage each do exactly one job.',
  },
  {
    title: 'Production practices',
    description:
      'Alembic migrations, a containerized Docker runtime, CI gates with linting, type checking, and tests, and deterministic deployment smoke checks.',
  },
  {
    title: 'Deployed end to end',
    description:
      'The API and PostgreSQL run on Render today, ingestion runs against the production database, and this frontend completes the public surface.',
  },
]

const TECH_STACK: string[] = [
  'Python',
  'PostgreSQL',
  'FastAPI',
  'Alembic',
  'SeleniumBase',
  'BeautifulSoup',
  'Docker',
  'GitHub Actions',
  'pytest',
  'uv',
  'React',
  'TypeScript',
  'Vite',
]

function Header() {
  return (
    <header className="site-header">
      <span className="wordmark">
        <CrosshairIcon />
        CS2 Analytics
      </span>
      <nav className="header-links">
        <a href={GITHUB_URL} target="_blank" rel="noreferrer">
          GitHub
        </a>
        <a href={`${API_BASE_URL}/docs`} target="_blank" rel="noreferrer">
          API Docs
        </a>
      </nav>
    </header>
  )
}

function CrosshairIcon() {
  return (
    <svg
      className="crosshair"
      viewBox="0 0 32 32"
      role="presentation"
      aria-hidden="true"
    >
      <circle cx="16" cy="16" r="8" fill="none" stroke="currentColor" strokeWidth="2.5" />
      <line x1="16" y1="2" x2="16" y2="10" stroke="currentColor" strokeWidth="2.5" />
      <line x1="16" y1="22" x2="16" y2="30" stroke="currentColor" strokeWidth="2.5" />
      <line x1="2" y1="16" x2="10" y2="16" stroke="currentColor" strokeWidth="2.5" />
      <line x1="22" y1="16" x2="30" y2="16" stroke="currentColor" strokeWidth="2.5" />
    </svg>
  )
}

function Hero() {
  return (
    <section className="hero">
      <p className="hero-kicker">End-to-end data engineering project</p>
      <h1>
        Professional Counter-Strike 2 match data,
        <span className="accent"> from scrape to served API</span>
      </h1>
      <p className="hero-sub">
        CS2 Analytics collects professional match, map, and player data through a
        resilient Python ingestion pipeline, stores it in PostgreSQL, and serves
        player statistics from a live FastAPI service.
      </p>
      <div className="hero-actions">
        <a
          className="button primary"
          href={`${API_BASE_URL}/docs`}
          target="_blank"
          rel="noreferrer"
        >
          Explore the live API
        </a>
        <a className="button" href={GITHUB_URL} target="_blank" rel="noreferrer">
          View source on GitHub
        </a>
      </div>
    </section>
  )
}

function PipelineSection() {
  return (
    <section className="section">
      <h2>How the system works</h2>
      <p className="section-sub">
        One pipeline, five stages — every piece below is running or deployed today.
      </p>
      <ol className="pipeline">
        {PIPELINE_STAGES.map((stage) => (
          <li key={stage.step} className="pipeline-card">
            <span className="pipeline-step">{stage.step}</span>
            <h3>{stage.title}</h3>
            <p>{stage.description}</p>
          </li>
        ))}
      </ol>
    </section>
  )
}

function HighlightsSection() {
  return (
    <section className="section">
      <h2>Engineering highlights</h2>
      <div className="highlights">
        {HIGHLIGHTS.map((item) => (
          <article key={item.title} className="highlight-card">
            <h3>{item.title}</h3>
            <p>{item.description}</p>
          </article>
        ))}
      </div>
    </section>
  )
}

function TechStackSection() {
  return (
    <section className="section">
      <h2>Built with</h2>
      <ul className="tech-chips">
        {TECH_STACK.map((tech) => (
          <li key={tech}>{tech}</li>
        ))}
      </ul>
    </section>
  )
}

function Footer() {
  return (
    <footer className="site-footer">
      <p>
        Built by Kyle Darden ·{' '}
        <a href={GITHUB_URL} target="_blank" rel="noreferrer">
          GitHub
        </a>{' '}
        ·{' '}
        <a href={`${API_BASE_URL}/docs`} target="_blank" rel="noreferrer">
          Live API
        </a>
      </p>
    </footer>
  )
}

function App() {
  return (
    <div className="page">
      <Header />
      <main>
        <Hero />
        <TopPlayersSection />
        <PipelineSection />
        <HighlightsSection />
        <TechStackSection />
      </main>
      <Footer />
    </div>
  )
}

export default App

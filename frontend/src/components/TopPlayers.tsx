import { useEffect, useState } from 'react'
import { API_BASE_URL } from '../config'

const MIN_MAPS = 1
const LIMIT = 10
const COLD_START_HINT_DELAY_MS = 5000

interface TopPlayer {
  player_name: string
  maps_played: number
  avg_rating: number
}

type FetchState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'success'; players: TopPlayer[] }

function useTopPlayers() {
  const [state, setState] = useState<FetchState>({ status: 'loading' })
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    const url = `${API_BASE_URL}/api/top_players?min_maps=${MIN_MAPS}&limit=${LIMIT}`

    setState({ status: 'loading' })

    fetch(url, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`The API responded with status ${response.status}`)
        }
        return response.json() as Promise<TopPlayer[]>
      })
      .then((players) => {
        setState({ status: 'success', players })
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) {
          return
        }
        const message =
          error instanceof Error ? error.message : 'Unexpected error'
        setState({ status: 'error', message })
      })

    return () => controller.abort()
  }, [attempt])

  const retry = () => setAttempt((current) => current + 1)

  return { state, retry }
}

function LoadingState() {
  const [showColdStartHint, setShowColdStartHint] = useState(false)

  useEffect(() => {
    const timer = setTimeout(
      () => setShowColdStartHint(true),
      COLD_START_HINT_DELAY_MS,
    )
    return () => clearTimeout(timer)
  }, [])

  return (
    <div className="players-status" role="status">
      <span className="pulse-dot" aria-hidden="true" />
      <p>
        {showColdStartHint
          ? 'Waking the API — the free-tier instance sleeps when idle and can take up to 30 seconds to respond.'
          : 'Loading top players…'}
      </p>
    </div>
  )
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="players-status players-error" role="alert">
      <p>Could not load top players. {message}.</p>
      <button type="button" className="button" onClick={onRetry}>
        Try again
      </button>
    </div>
  )
}

function EmptyState() {
  return (
    <div className="players-status">
      <p>
        No players matched the current filters. The database may be between
        ingestion runs — check back soon.
      </p>
    </div>
  )
}

function PlayersTable({ players }: { players: TopPlayer[] }) {
  return (
    <div className="players-table-wrap">
      <table
        className="players-table"
        aria-label="Top players by average rating"
      >
        <thead>
          <tr>
            <th scope="col" className="rank-col">#</th>
            <th scope="col">Player</th>
            <th scope="col" className="num-col">Maps</th>
            <th scope="col" className="num-col">Avg rating</th>
          </tr>
        </thead>
        <tbody>
          {players.map((player, index) => (
            <tr key={player.player_name}>
              <td className="rank-col">{index + 1}</td>
              <td className="player-name">{player.player_name}</td>
              <td className="num-col">{player.maps_played}</td>
              <td className="num-col rating">{player.avg_rating.toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function TopPlayersSection() {
  const { state, retry } = useTopPlayers()

  return (
    <section className="section" id="top-players">
      <h2>Top players, live from the API</h2>
      <p className="section-sub">
        The {LIMIT} highest-rated players currently in the production database,
        fetched from the deployed REST API when this page loads.
      </p>
      {state.status === 'loading' && <LoadingState />}
      {state.status === 'error' && (
        <ErrorState message={state.message} onRetry={retry} />
      )}
      {state.status === 'success' &&
        (state.players.length === 0 ? (
          <EmptyState />
        ) : (
          <PlayersTable players={state.players} />
        ))}
    </section>
  )
}

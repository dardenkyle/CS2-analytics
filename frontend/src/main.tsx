import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

const rootElement = document.getElementById('root')

if (rootElement === null) {
  throw new Error('Root element "#root" was not found in the document')
}

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

import { GoldCoastMap } from './components/GoldCoastMap.tsx'

export function App() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <h1 className="app-title">Gold Coast Remote Sensing</h1>
        <p className="app-subtitle">Study area: City of Gold Coast local government area</p>
      </header>
      <main className="app-main">
        <GoldCoastMap />
      </main>
    </div>
  )
}

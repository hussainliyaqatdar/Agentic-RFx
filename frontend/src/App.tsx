import { Route, Routes } from 'react-router-dom'
import { AppHeader } from './components/AppHeader'
import RfxDetailPage from './pages/RfxDetailPage'
import RfxListPage from './pages/RfxListPage'

export default function App() {
  return (
    <div className="min-h-screen bg-bg-page">
      <AppHeader />
      <main className="mx-auto max-w-6xl px-6 py-8">
        <Routes>
          <Route path="/" element={<RfxListPage />} />
          <Route path="/rfx/:rfxId" element={<RfxDetailPage />} />
        </Routes>
      </main>
    </div>
  )
}

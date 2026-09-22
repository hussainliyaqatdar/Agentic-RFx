import { useEffect, useState } from 'react'
import { NavLink, Route, Routes } from 'react-router-dom'
import { apiGet } from './lib/api'
import AnalystChatPage from './pages/AnalystChatPage'
import ComparisonPage from './pages/ComparisonPage'
import RfxCopilotPage from './pages/RfxCopilotPage'
import RfxListPage from './pages/RfxListPage'

type BackendStatus = 'checking' | 'up' | 'down'

const navItems = [
  { to: '/', label: 'RFx list', end: true },
  { to: '/rfx/new', label: 'Co-pilot' },
  { to: '/rfx/1/comparison', label: 'Comparison' },
  { to: '/rfx/1/chat', label: 'Analyst chat' },
]

function BackendStatusBadge() {
  const [status, setStatus] = useState<BackendStatus>('checking')

  useEffect(() => {
    apiGet('/health')
      .then(() => setStatus('up'))
      .catch(() => setStatus('down'))
  }, [])

  const dotColor = status === 'up' ? 'bg-emerald-500' : status === 'down' ? 'bg-red-500' : 'bg-slate-300'
  const label = status === 'up' ? 'backend connected' : status === 'down' ? 'backend unreachable' : 'checking backend…'

  return (
    <span className="flex items-center gap-2 text-xs text-slate-500">
      <span className={`h-2 w-2 rounded-full ${dotColor}`} />
      {label}
    </span>
  )
}

export default function App() {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-8">
            <span className="text-sm font-semibold tracking-tight text-slate-900">Agentic RFx</span>
            <nav className="flex gap-5">
              {navItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) =>
                    `text-sm ${isActive ? 'font-medium text-slate-900' : 'text-slate-500 hover:text-slate-700'}`
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </nav>
          </div>
          <BackendStatusBadge />
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-8">
        <Routes>
          <Route path="/" element={<RfxListPage />} />
          <Route path="/rfx/new" element={<RfxCopilotPage />} />
          <Route path="/rfx/:rfxId/comparison" element={<ComparisonPage />} />
          <Route path="/rfx/:rfxId/chat" element={<AnalystChatPage />} />
        </Routes>
      </main>
    </div>
  )
}

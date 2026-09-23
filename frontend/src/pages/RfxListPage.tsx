import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CopilotDrawer } from '../components/CopilotDrawer'
import { Button } from '../components/Button'
import { ChevronDownIcon, PlusIcon, SparkleIcon } from '../components/icons'
import { RfxStatusPill } from '../components/StatusPill'
import { rfxApi, type RfxSummary } from '../lib/api'

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
}

export default function RfxListPage() {
  const navigate = useNavigate()
  const [rows, setRows] = useState<RfxSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [menuOpen, setMenuOpen] = useState(false)
  const [copilotOpen, setCopilotOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  function refresh() {
    rfxApi.list().then(setRows).catch((err) => setError(err instanceof Error ? err.message : 'Failed to load'))
  }

  useEffect(() => {
    refresh()
    function onClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false)
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [])

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">RFx</h1>
          <p className="mt-1 text-sm text-text-secondary">Requests for quote sent out to your vendor panel.</p>
        </div>
        <div className="relative" ref={menuRef}>
          <Button onClick={() => setMenuOpen((v) => !v)}>
            <PlusIcon width={16} height={16} />
            Create new RFx
            <ChevronDownIcon width={14} height={14} />
          </Button>
          {menuOpen && (
            <div className="absolute right-0 z-10 mt-2 w-64 overflow-hidden rounded-lg border border-border-default bg-white shadow-lg">
              <button
                onClick={() => {
                  setMenuOpen(false)
                  setCopilotOpen(true)
                }}
                className="flex w-full items-start gap-2.5 px-4 py-3 text-left hover:bg-bg-hover"
              >
                <SparkleIcon className="mt-0.5 shrink-0 text-brand-blue" width={16} height={16} />
                <span>
                  <span className="block text-sm font-medium text-text-primary">Use Agentic RFx</span>
                  <span className="block text-xs text-text-secondary">Talk it into existence with the AI co-pilot</span>
                </span>
              </button>
              <button
                disabled
                title="Not part of this v0 - see project README"
                className="flex w-full items-start gap-2.5 border-t border-border-default px-4 py-3 text-left opacity-50"
              >
                <span className="mt-0.5 h-4 w-4 shrink-0 rounded border border-text-tertiary" />
                <span>
                  <span className="block text-sm font-medium text-text-primary">Create manually</span>
                  <span className="block text-xs text-text-secondary">Build the RFx from a blank form</span>
                </span>
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border border-border-default bg-white">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border-default text-left text-xs font-semibold uppercase tracking-wide text-text-secondary">
              <th className="px-5 py-3">RFx</th>
              <th className="px-5 py-3">Category</th>
              <th className="px-5 py-3">Line items</th>
              <th className="px-5 py-3">Vendors</th>
              <th className="px-5 py-3">Created</th>
              <th className="px-5 py-3">Status</th>
            </tr>
          </thead>
          <tbody>
            {rows?.map((rfx) => (
              <tr
                key={rfx.id}
                onClick={() => navigate(`/rfx/${rfx.id}`)}
                className="cursor-pointer border-b border-border-default last:border-0 hover:bg-bg-hover"
              >
                <td className="px-5 py-3.5 font-medium text-text-primary">{rfx.title}</td>
                <td className="px-5 py-3.5 text-text-secondary">{rfx.category}</td>
                <td className="px-5 py-3.5 text-text-secondary">{rfx.line_item_count}</td>
                <td className="px-5 py-3.5 text-text-secondary">{rfx.vendor_count}</td>
                <td className="px-5 py-3.5 text-text-secondary">{formatDate(rfx.created_at)}</td>
                <td className="px-5 py-3.5">
                  <RfxStatusPill status={rfx.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows?.length === 0 && (
          <p className="px-5 py-10 text-center text-sm text-text-secondary">
            No RFx yet - create one with the AI co-pilot to get started.
          </p>
        )}
        {error && <p className="px-5 py-4 text-sm text-danger-text">{error}</p>}
      </div>

      {copilotOpen && (
        <CopilotDrawer
          onClose={() => setCopilotOpen(false)}
          onFinalized={(rfxId) => {
            setCopilotOpen(false)
            refresh()
            navigate(`/rfx/${rfxId}`)
          }}
        />
      )}
    </div>
  )
}

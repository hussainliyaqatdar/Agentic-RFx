import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Button } from '../components/Button'
import { ComparisonGrid } from '../components/ComparisonGrid'
import { ChevronLeftIcon, SparkleIcon } from '../components/icons'
import { RfxStatusPill } from '../components/StatusPill'
import { VendorDetailDrawer } from '../components/VendorDetailDrawer'
import { rfxApi, type ComparisonData, type RfxDetail } from '../lib/api'

type Tab = 'review' | 'responses'

function formatSpec(spec: RfxDetail['line_items'][number]['spec_attributes']): string {
  if (spec.summary) return spec.summary
  const parts: string[] = []
  if (spec.ply) parts.push(`${spec.ply}-ply`)
  if (spec.flute && spec.flute !== '-') parts.push(`${spec.flute}-flute`)
  if (spec.dimensions_mm) parts.push(`${spec.dimensions_mm}mm`)
  if (spec.gsm) parts.push(`${spec.gsm} GSM`)
  if (spec.printed) parts.push('printed')
  return parts.length ? parts.join(', ') : '—'
}

export default function RfxDetailPage() {
  const { rfxId } = useParams()
  const navigate = useNavigate()
  const [rfx, setRfx] = useState<RfxDetail | null>(null)
  const [tab, setTab] = useState<Tab>('review')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function refresh() {
    rfxApi.get(Number(rfxId)).then(setRfx).catch((err) => setError(err instanceof Error ? err.message : 'Failed to load'))
  }

  useEffect(refresh, [rfxId])

  async function handleSend() {
    setSending(true)
    setError(null)
    try {
      await rfxApi.send(Number(rfxId))
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not send the RFx')
    } finally {
      setSending(false)
    }
  }

  if (error) return <p className="text-sm text-danger-text">{error}</p>
  if (!rfx) return <p className="text-sm text-text-secondary">Loading…</p>

  return (
    <div>
      <button onClick={() => navigate('/')} className="mb-3 flex items-center gap-1 text-sm text-text-secondary hover:text-text-primary">
        <ChevronLeftIcon width={16} height={16} />
        Back to RFx list
      </button>

      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-semibold text-text-primary">{rfx.title}</h1>
          <RfxStatusPill status={rfx.status} />
        </div>
        {rfx.status === 'draft' && (
          <Button onClick={handleSend} disabled={sending}>
            {sending ? 'Sending…' : `Send to ${rfx.vendors.length || 5} vendors`}
          </Button>
        )}
      </div>

      <div className="mb-6 flex gap-6 border-b border-border-default">
        {(['review', 'responses'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`border-b-2 pb-3 text-sm font-medium ${
              tab === t ? 'border-brand-blue text-brand-blue' : 'border-transparent text-text-secondary hover:text-text-primary'
            }`}
          >
            {t === 'review' ? 'Review RFx' : 'Vendor Responses'}
          </button>
        ))}
      </div>

      {tab === 'review' ? <ReviewTab rfx={rfx} /> : <ResponsesTab rfx={rfx} rfxId={Number(rfxId)} />}
    </div>
  )
}

function ReviewTab({ rfx }: { rfx: RfxDetail }) {
  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-border-default bg-white p-5">
        <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-text-secondary">Scope &amp; terms</p>
        <p className="mb-4 text-sm text-text-primary">{rfx.scope_description}</p>
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div>
            <p className="text-text-tertiary">Payment terms</p>
            <p className="text-text-primary">{rfx.payment_terms ?? '—'}</p>
          </div>
          <div>
            <p className="text-text-tertiary">Delivery terms</p>
            <p className="text-text-primary">{rfx.delivery_terms ?? '—'}</p>
          </div>
          <div>
            <p className="text-text-tertiary">Quote validity</p>
            <p className="text-text-primary">{rfx.validity_days ? `${rfx.validity_days} days` : '—'}</p>
          </div>
        </div>
      </section>

      <section>
        <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-text-secondary">
          Line items ({rfx.line_items.length})
        </p>
        <div className="overflow-hidden rounded-xl border border-border-default bg-white">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border-default text-left text-xs font-semibold uppercase tracking-wide text-text-secondary">
                <th className="px-4 py-2.5">SKU</th>
                <th className="px-4 py-2.5">Description</th>
                <th className="px-4 py-2.5">Spec</th>
                <th className="px-4 py-2.5">Qty</th>
                <th className="px-4 py-2.5">Unit</th>
              </tr>
            </thead>
            <tbody>
              {rfx.line_items.map((li) => (
                <tr key={li.id} className="border-b border-border-default text-text-primary last:border-0">
                  <td className="px-4 py-2.5 font-mono text-xs">
                    {li.sku_code.startsWith('NEW-') ? (
                      <span className="rounded bg-warning-bg px-1.5 py-0.5 text-warning-text">new</span>
                    ) : (
                      li.sku_code
                    )}
                  </td>
                  <td className="px-4 py-2.5">{li.description}</td>
                  <td className="px-4 py-2.5 text-text-secondary">{formatSpec(li.spec_attributes)}</td>
                  <td className="px-4 py-2.5">{li.quantity.toLocaleString('en-IN')}</td>
                  <td className="px-4 py-2.5 text-text-secondary">{li.unit}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-text-secondary">
          Quality questionnaire ({rfx.questions.length})
        </p>
        <div className="space-y-2">
          {rfx.questions.map((q) => (
            <div key={q.id} className="rounded-lg border border-border-default bg-white px-4 py-2.5 text-sm text-text-primary">
              {q.question_no}. {q.question_text}
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}

function ResponsesTab({ rfx, rfxId }: { rfx: RfxDetail; rfxId: number }) {
  const [comparison, setComparison] = useState<ComparisonData | null>(null)
  const [loading, setLoading] = useState(true)
  const [extracting, setExtracting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [openVendorId, setOpenVendorId] = useState<number | null>(null)

  function loadComparison() {
    setLoading(true)
    rfxApi
      .comparison(rfxId)
      .then(setComparison)
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load'))
      .finally(() => setLoading(false))
  }

  useEffect(loadComparison, [rfxId])

  async function handleExtract() {
    setExtracting(true)
    setError(null)
    try {
      await rfxApi.extract(rfxId)
      loadComparison()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Extraction failed')
    } finally {
      setExtracting(false)
    }
  }

  if (rfx.status === 'draft') {
    return (
      <p className="rounded-xl border border-dashed border-border-strong bg-white px-5 py-10 text-center text-sm text-text-secondary">
        Send this RFx to vendors first - responses will land here once they come in.
      </p>
    )
  }

  const hasAnyExtraction = comparison?.rows.some((r) => Object.values(r.cells).some((c) => c != null))

  return (
    <div className="space-y-4">
      {error && <p className="text-sm text-danger-text">{error}</p>}
      {loading && <p className="text-sm text-text-secondary">Loading…</p>}

      {!loading && !hasAnyExtraction && (
        <div className="rounded-xl border border-dashed border-border-strong bg-white px-5 py-10 text-center">
          <p className="mb-3 text-sm text-text-secondary">
            Vendor responses haven't been processed yet. This runs the real extraction pipeline (worker +
            evaluator agents) against each vendor's documents - real AI calls, takes a couple of minutes.
          </p>
          <Button onClick={handleExtract} disabled={extracting}>
            {extracting ? 'Processing vendor responses…' : 'Process vendor responses'}
          </Button>
        </div>
      )}

      {!loading && hasAnyExtraction && comparison && (
        <ComparisonGrid data={comparison} onOpenVendor={setOpenVendorId} />
      )}

      <button
        disabled
        title="Analyst chat is module 5 - not built yet"
        className="flex items-center gap-2 rounded-lg border border-border-default bg-white px-4 py-2.5 text-sm text-text-tertiary opacity-60"
      >
        <SparkleIcon width={16} height={16} />
        Ask the analyst chat about these responses
      </button>

      {openVendorId != null && (
        <VendorDetailDrawer rfxId={rfxId} vendorId={openVendorId} onClose={() => setOpenVendorId(null)} />
      )}
    </div>
  )
}

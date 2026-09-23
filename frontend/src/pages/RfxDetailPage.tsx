import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { AnalystChatDrawer } from '../components/AnalystChatDrawer'
import { AwardPanel } from '../components/AwardPanel'
import { Button, IconButton } from '../components/Button'
import { ComparisonGrid } from '../components/ComparisonGrid'
import { CheckIcon, ChevronLeftIcon, PencilIcon, PlusIcon, SparkleIcon, XIcon } from '../components/icons'
import { RfxStatusPill } from '../components/StatusPill'
import { VendorDetailDrawer } from '../components/VendorDetailDrawer'
import { rfxApi, type ComparisonData, type ProposedAwardLine, type RfxDetail } from '../lib/api'

type Tab = 'responses' | 'review'

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
  const [tab, setTab] = useState<Tab>('responses')
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
        {(['responses', 'review'] as Tab[]).map((t) => (
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

      {tab === 'review' ? (
        <ReviewTab rfx={rfx} onUpdated={refresh} />
      ) : (
        <ResponsesTab rfx={rfx} rfxId={Number(rfxId)} onAwarded={refresh} onRefresh={refresh} />
      )}
    </div>
  )
}

function ReviewTab({ rfx, onUpdated }: { rfx: RfxDetail; onUpdated: () => void }) {
  const canEdit = rfx.status === 'draft'
  const [editingId, setEditingId] = useState<number | null>(null)

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
                {canEdit && <th className="px-4 py-2.5" />}
              </tr>
            </thead>
            <tbody>
              {rfx.line_items.map((li) => (
                <LineItemRow
                  key={li.id}
                  rfxId={rfx.id}
                  item={li}
                  canEdit={canEdit}
                  editing={editingId === li.id}
                  onStartEdit={() => setEditingId(li.id)}
                  onCancelEdit={() => setEditingId(null)}
                  onSaved={() => {
                    setEditingId(null)
                    onUpdated()
                  }}
                />
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

function LineItemRow({
  rfxId,
  item,
  canEdit,
  editing,
  onStartEdit,
  onCancelEdit,
  onSaved,
}: {
  rfxId: number
  item: RfxDetail['line_items'][number]
  canEdit: boolean
  editing: boolean
  onStartEdit: () => void
  onCancelEdit: () => void
  onSaved: () => void
}) {
  const [description, setDescription] = useState(item.description)
  const [spec, setSpec] = useState(formatSpec(item.spec_attributes))
  const [quantity, setQuantity] = useState(String(item.quantity))
  const [unit, setUnit] = useState(item.unit)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (editing) {
      setDescription(item.description)
      setSpec(formatSpec(item.spec_attributes))
      setQuantity(String(item.quantity))
      setUnit(item.unit)
      setError(null)
    }
  }, [editing, item])

  async function handleSave() {
    setSaving(true)
    setError(null)
    try {
      await rfxApi.updateLineItem(rfxId, item.id, {
        description,
        spec_summary: spec,
        quantity: Number(quantity),
        unit,
      })
      onSaved()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save')
    } finally {
      setSaving(false)
    }
  }

  const skuCell = (
    <td className="px-4 py-2.5 align-top font-mono text-xs">
      {item.sku_code.startsWith('NEW-') ? (
        <span className="rounded bg-warning-bg px-1.5 py-0.5 text-warning-text">new</span>
      ) : (
        item.sku_code
      )}
    </td>
  )

  if (!editing) {
    return (
      <tr className="border-b border-border-default text-text-primary last:border-0">
        {skuCell}
        <td className="px-4 py-2.5">{item.description}</td>
        <td className="px-4 py-2.5 text-text-secondary">{formatSpec(item.spec_attributes)}</td>
        <td className="px-4 py-2.5">{item.quantity.toLocaleString('en-IN')}</td>
        <td className="px-4 py-2.5 text-text-secondary">{item.unit}</td>
        {canEdit && (
          <td className="px-4 py-2.5">
            <IconButton onClick={onStartEdit} aria-label="Edit line item">
              <PencilIcon width={14} height={14} />
            </IconButton>
          </td>
        )}
      </tr>
    )
  }

  return (
    <tr className="border-b border-border-default bg-bg-hover text-text-primary last:border-0">
      {skuCell}
      <td className="px-4 py-2.5 align-top">
        <input
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="w-full rounded-lg border border-border-strong px-2 py-1.5 text-sm"
        />
      </td>
      <td className="px-4 py-2.5 align-top">
        <input
          value={spec}
          onChange={(e) => setSpec(e.target.value)}
          className="w-full rounded-lg border border-border-strong px-2 py-1.5 text-sm"
        />
      </td>
      <td className="px-4 py-2.5 align-top">
        <input
          type="number"
          min={0}
          value={quantity}
          onChange={(e) => setQuantity(e.target.value)}
          className="w-24 rounded-lg border border-border-strong px-2 py-1.5 text-sm"
        />
      </td>
      <td className="px-4 py-2.5 align-top">
        <input
          value={unit}
          onChange={(e) => setUnit(e.target.value)}
          className="w-20 rounded-lg border border-border-strong px-2 py-1.5 text-sm"
        />
      </td>
      <td className="px-4 py-2.5 align-top">
        <div className="flex items-center gap-1.5">
          <IconButton onClick={handleSave} disabled={saving} aria-label="Save">
            <CheckIcon width={14} height={14} />
          </IconButton>
          <IconButton onClick={onCancelEdit} disabled={saving} aria-label="Cancel">
            <XIcon width={14} height={14} />
          </IconButton>
        </div>
        {error && <p className="mt-1 text-xs text-danger-text">{error}</p>}
      </td>
    </tr>
  )
}

function ResponsesTab({
  rfx,
  rfxId,
  onAwarded,
  onRefresh,
}: {
  rfx: RfxDetail
  rfxId: number
  onAwarded: () => void
  onRefresh: () => void
}) {
  const [comparison, setComparison] = useState<ComparisonData | null>(null)
  const [loading, setLoading] = useState(true)
  const [extracting, setExtracting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [openVendorId, setOpenVendorId] = useState<number | null>(null)
  const [chatOpen, setChatOpen] = useState(false)
  const [awardPrefill, setAwardPrefill] = useState<ProposedAwardLine[] | null>(null)
  const [awardOpen, setAwardOpen] = useState(false)

  const isExtracting = rfx.vendors.some((v) => v.response_status === 'extracting')
  const wasExtractingRef = useRef(isExtracting)

  function loadComparison() {
    setLoading(true)
    rfxApi
      .comparison(rfxId)
      .then(setComparison)
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load'))
      .finally(() => setLoading(false))
  }

  useEffect(loadComparison, [rfxId])

  // Another tab, or a page reload mid-run, may have left extraction in
  // progress server-side - poll until it's done instead of showing a stale button,
  // and keep the grid's cells current as each vendor finishes.
  useEffect(() => {
    if (!isExtracting) return
    const interval = setInterval(() => {
      onRefresh()
      loadComparison()
    }, 4000)
    return () => clearInterval(interval)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isExtracting, onRefresh])

  useEffect(() => {
    if (wasExtractingRef.current && !isExtracting) {
      loadComparison()
    }
    wasExtractingRef.current = isExtracting
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isExtracting])

  async function handleExtract() {
    setExtracting(true)
    setError(null)
    try {
      await rfxApi.extract(rfxId)
      loadComparison()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Extraction failed')
      onRefresh()
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
          {isExtracting ? (
            <p className="text-sm font-medium text-text-primary">Still processing vendor responses…</p>
          ) : (
            <Button onClick={handleExtract} disabled={extracting}>
              {extracting ? 'Processing vendor responses…' : 'Process vendor responses'}
            </Button>
          )}
        </div>
      )}

      {!loading && hasAnyExtraction && comparison && (
        <>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-text-secondary">
              <span className="flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-success-text" /> confirmed
              </span>
              <span className="flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-warning-text" /> needs review
              </span>
              <span className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-sm border border-success-text bg-success-bg" /> cheapest
              </span>
              <span className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-sm border border-danger-text bg-danger-bg" /> priciest
              </span>
              <span>Click any price for its source and reasoning.</span>
            </div>
            <div className="flex shrink-0 items-center gap-3">
              <button
                onClick={() => setChatOpen(true)}
                className="flex items-center gap-2 rounded-lg border border-border-default bg-white px-4 py-2.5 text-sm text-text-primary hover:bg-bg-hover"
              >
                <SparkleIcon width={16} height={16} className="text-brand-blue" />
                Ask the analyst chat about these responses
              </button>
              {rfx.status !== 'awarded' && (
                <Button onClick={() => { setAwardPrefill(null); setAwardOpen(true) }}>
                  Award decision
                </Button>
              )}
            </div>
          </div>

          <ComparisonGrid data={comparison} onOpenVendor={setOpenVendorId} />
        </>
      )}

      {openVendorId != null && (
        <VendorDetailDrawer rfxId={rfxId} vendorId={openVendorId} onClose={() => setOpenVendorId(null)} />
      )}

      {chatOpen && (
        <AnalystChatDrawer
          rfxId={rfxId}
          onClose={() => setChatOpen(false)}
          onApplyAward={(awards) => {
            setAwardPrefill(awards)
            setChatOpen(false)
            setAwardOpen(true)
          }}
        />
      )}

      {awardOpen && comparison && (
        <AwardPanel
          rfxId={rfxId}
          comparison={comparison}
          prefill={awardPrefill}
          onClose={() => setAwardOpen(false)}
          onAwarded={() => {
            setAwardOpen(false)
            onAwarded()
          }}
        />
      )}
    </div>
  )
}

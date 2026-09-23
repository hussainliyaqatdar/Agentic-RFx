import { useState } from 'react'
import type { ComparisonCell, ComparisonData, ComparisonRow, ComparisonVendorColumn } from '../lib/api'
import { AlertTriangleIcon } from './icons'

function formatPrice(cell: ComparisonCell | null) {
  if (!cell || cell.unit_price_normalized == null) return null
  return cell.unit_price_normalized.toLocaleString('en-IN', { maximumFractionDigits: 2 })
}

function confidenceDotClass(cell: ComparisonCell) {
  if (cell.needs_review) return 'bg-warning-text'
  const conf = Math.min(cell.extraction_confidence ?? 1, cell.match_confidence ?? 1)
  if (conf < 0.7) return 'bg-warning-text'
  return 'bg-success-text'
}

interface Props {
  data: ComparisonData
  onOpenVendor: (vendorId: number) => void
}

export function ComparisonGrid({ data, onOpenVendor }: Props) {
  const [selected, setSelected] = useState<{ row: ComparisonRow; vendor: ComparisonVendorColumn; cell: ComparisonCell } | null>(null)

  return (
    <div>
      <div className="overflow-auto rounded-xl border border-border-default bg-white" style={{ maxHeight: 560 }}>
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr>
              <th className="sticky top-0 left-0 z-20 min-w-[260px] border-b border-r border-border-default bg-bg-page px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-text-secondary">
                Line item
              </th>
              {data.vendors.map((v) => (
                <th
                  key={v.rfx_vendor_id}
                  className="sticky top-0 z-10 min-w-[140px] cursor-pointer border-b border-border-default bg-bg-page px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-text-secondary hover:text-brand-blue"
                  onClick={() => onOpenVendor(v.vendor_id)}
                  title="View attachments and questionnaire answers"
                >
                  {v.name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.rows.map((row) => (
              <tr key={row.line_item_id} className="border-b border-border-default last:border-0 hover:bg-bg-hover">
                <td className="sticky left-0 z-10 border-r border-border-default bg-white px-4 py-2.5 align-top">
                  <p className="font-mono text-xs text-text-tertiary">{row.sku_code}</p>
                  <p className="text-text-primary">{row.description}</p>
                  <p className="text-xs text-text-secondary">
                    {row.quantity.toLocaleString('en-IN')} {row.unit}
                  </p>
                </td>
                {data.vendors.map((v) => {
                  const cell = row.cells[String(v.rfx_vendor_id)]
                  const price = formatPrice(cell)
                  return (
                    <td
                      key={v.rfx_vendor_id}
                      onClick={() => cell && setSelected({ row, vendor: v, cell })}
                      className={`px-4 py-2.5 align-top ${cell ? 'cursor-pointer' : ''}`}
                    >
                      {cell && price != null ? (
                        <span className="flex items-center gap-1.5">
                          <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${confidenceDotClass(cell)}`} />
                          <span className="text-text-primary">
                            {cell.currency_normalized} {price}
                          </span>
                        </span>
                      ) : v.response_status === 'pending' ? (
                        <span className="italic text-text-tertiary">processing…</span>
                      ) : (
                        <span className="text-text-tertiary">not quoted</span>
                      )}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-3 flex items-center gap-4 text-xs text-text-secondary">
        <span className="flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-success-text" /> confirmed
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-warning-text" /> needs review
        </span>
        <span>Click any price for its source and reasoning.</span>
      </div>

      {selected && (
        <CellDetail
          row={selected.row}
          vendor={selected.vendor}
          cell={selected.cell}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  )
}

function CellDetail({
  row,
  vendor,
  cell,
  onClose,
}: {
  row: ComparisonRow
  vendor: ComparisonVendorColumn
  cell: ComparisonCell
  onClose: () => void
}) {
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/30 p-6" onClick={onClose}>
      <div
        className="max-h-[80vh] w-full max-w-lg overflow-y-auto rounded-xl bg-white p-5 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <p className="text-xs font-semibold uppercase tracking-wide text-text-secondary">{vendor.name}</p>
        <h3 className="mt-1 text-base font-semibold text-text-primary">{row.description}</h3>
        <p className="mb-4 text-xs text-text-tertiary">{row.sku_code}</p>

        {cell.needs_review && (
          <div className="mb-4 flex items-start gap-2 rounded-lg bg-warning-bg px-3 py-2 text-xs text-warning-text">
            <AlertTriangleIcon width={14} height={14} className="mt-0.5 shrink-0" />
            <span>Flagged for review{cell.evaluator_verdict ? ` — evaluator marked this ${cell.evaluator_verdict.toLowerCase().replace(/_/g, ' ')}` : ''}.</span>
          </div>
        )}

        <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
          <div>
            <dt className="text-xs text-text-tertiary">Normalized price</dt>
            <dd className="text-text-primary">
              {cell.currency_normalized} {cell.unit_price_normalized?.toLocaleString('en-IN')}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-text-tertiary">Lead time</dt>
            <dd className="text-text-primary">{cell.lead_time_days ? `${cell.lead_time_days} days` : '—'}</dd>
          </div>
          <div>
            <dt className="text-xs text-text-tertiary">Extraction confidence</dt>
            <dd className="text-text-primary">
              {cell.extraction_confidence != null ? `${Math.round(cell.extraction_confidence * 100)}%` : '—'}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-text-tertiary">Match confidence</dt>
            <dd className="text-text-primary">
              {cell.match_confidence != null ? `${Math.round(cell.match_confidence * 100)}%` : '—'}
            </dd>
          </div>
        </dl>

        <div className="mt-4 space-y-3 text-sm">
          <div>
            <p className="text-xs text-text-tertiary">Vendor's own description</p>
            <p className="text-text-primary">{cell.vendor_raw_description || '—'}</p>
          </div>
          {cell.conversion_notes && (
            <div>
              <p className="text-xs text-text-tertiary">Conversion notes</p>
              <p className="text-text-primary">{cell.conversion_notes}</p>
            </div>
          )}
          {cell.source_citation && (
            <div>
              <p className="text-xs text-text-tertiary">Source</p>
              <p className="text-text-secondary italic">{cell.source_citation}</p>
            </div>
          )}
          {cell.evaluator_reasoning && (
            <div>
              <p className="text-xs text-text-tertiary">Evaluator's assessment</p>
              <p className="text-text-primary">{cell.evaluator_reasoning}</p>
            </div>
          )}
        </div>

        <button onClick={onClose} className="mt-5 text-sm font-medium text-brand-blue">
          Close
        </button>
      </div>
    </div>
  )
}

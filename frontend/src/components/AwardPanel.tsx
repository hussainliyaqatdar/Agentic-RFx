import { useMemo, useState } from 'react'
import { rfxApi, type ComparisonData, type ProposedAwardLine } from '../lib/api'
import { Button, IconButton } from './Button'
import { XIcon } from './icons'

interface Props {
  rfxId: number
  comparison: ComparisonData
  prefill: ProposedAwardLine[] | null
  onClose: () => void
  onAwarded: () => void
}

function defaultAwards(comparison: ComparisonData, prefill: ProposedAwardLine[] | null): Record<string, number> {
  const awards: Record<string, number> = {}
  const prefillBySku = new Map((prefill ?? []).map((p) => [p.sku_code, p.vendor_id]))
  for (const row of comparison.rows) {
    if (prefillBySku.has(row.sku_code)) {
      awards[row.sku_code] = prefillBySku.get(row.sku_code)!
      continue
    }
    let cheapestVendorId: number | null = null
    let cheapestPrice = Infinity
    for (const vendor of comparison.vendors) {
      const cell = row.cells[String(vendor.rfx_vendor_id)]
      if (cell && cell.unit_price_normalized != null && cell.unit_price_normalized < cheapestPrice) {
        cheapestPrice = cell.unit_price_normalized
        cheapestVendorId = vendor.vendor_id
      }
    }
    if (cheapestVendorId != null) awards[row.sku_code] = cheapestVendorId
  }
  return awards
}

export function AwardPanel({ rfxId, comparison, prefill, onClose, onAwarded }: Props) {
  const [awards, setAwards] = useState<Record<string, number>>(() => defaultAwards(comparison, prefill))
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const rfxVendorByVendorId = useMemo(
    () => new Map(comparison.vendors.map((v) => [v.vendor_id, v])),
    [comparison.vendors],
  )

  const { totalsByVendor, grandTotal, unassignedCount } = useMemo(() => {
    const byVendor = new Map<number, number>()
    let total = 0
    let unassigned = 0
    for (const row of comparison.rows) {
      const vendorId = awards[row.sku_code]
      if (vendorId == null) {
        unassigned += 1
        continue
      }
      const rv = rfxVendorByVendorId.get(vendorId)
      const cell = rv ? row.cells[String(rv.rfx_vendor_id)] : null
      const price = cell?.unit_price_normalized ?? 0
      const lineTotal = price * row.quantity
      total += lineTotal
      byVendor.set(vendorId, (byVendor.get(vendorId) ?? 0) + lineTotal)
    }
    return { totalsByVendor: byVendor, grandTotal: total, unassignedCount: unassigned }
  }, [awards, comparison.rows, rfxVendorByVendorId])

  async function handleConfirm() {
    setSubmitting(true)
    setError(null)
    try {
      await rfxApi.award(rfxId, awards)
      onAwarded()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not commit the award')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/30 p-6">
      <div className="flex max-h-[85vh] w-full max-w-3xl flex-col rounded-xl bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-border-default px-5 py-4">
          <div>
            <h3 className="text-base font-semibold text-text-primary">Award decision</h3>
            <p className="text-xs text-text-secondary">
              Defaults to the cheapest quoting vendor per line - override any row, then confirm.
            </p>
          </div>
          <IconButton onClick={onClose} aria-label="Close">
            <XIcon width={16} height={16} />
          </IconButton>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-3">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border-default text-left text-xs font-semibold uppercase tracking-wide text-text-secondary">
                <th className="py-2">Line item</th>
                <th className="py-2">Awarded to</th>
                <th className="py-2 text-right">Line total</th>
              </tr>
            </thead>
            <tbody>
              {comparison.rows.map((row) => {
                const options = comparison.vendors
                  .map((v) => ({ vendor: v, cell: row.cells[String(v.rfx_vendor_id)] }))
                  .filter((o) => o.cell && o.cell.unit_price_normalized != null)
                const selectedVendorId = awards[row.sku_code]
                const selectedCell = selectedVendorId != null
                  ? row.cells[String(rfxVendorByVendorId.get(selectedVendorId)?.rfx_vendor_id)]
                  : null
                const lineTotal = selectedCell?.unit_price_normalized != null
                  ? selectedCell.unit_price_normalized * row.quantity
                  : null
                return (
                  <tr key={row.line_item_id} className="border-b border-border-default last:border-0">
                    <td className="py-2 pr-3">
                      <p className="font-mono text-xs text-text-tertiary">{row.sku_code}</p>
                      <p className="text-text-primary">{row.description}</p>
                    </td>
                    <td className="py-2 pr-3">
                      {options.length === 0 ? (
                        <span className="text-xs italic text-text-tertiary">no vendor quoted this line</span>
                      ) : (
                        <select
                          value={selectedVendorId ?? ''}
                          onChange={(e) =>
                            setAwards((prev) => ({ ...prev, [row.sku_code]: Number(e.target.value) }))
                          }
                          className="rounded-lg border border-border-strong px-2 py-1.5 text-sm"
                        >
                          {options.map(({ vendor, cell }) => (
                            <option key={vendor.vendor_id} value={vendor.vendor_id}>
                              {vendor.name} — {cell!.currency_normalized} {cell!.unit_price_normalized}/unit
                              {cell!.needs_review ? ' (review)' : ''}
                            </option>
                          ))}
                        </select>
                      )}
                    </td>
                    <td className="py-2 text-right text-text-primary">
                      {lineTotal != null ? lineTotal.toLocaleString('en-IN', { maximumFractionDigits: 0 }) : '—'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        <div className="border-t border-border-default px-5 py-4">
          {unassignedCount > 0 && (
            <p className="mb-2 text-xs text-danger-text">
              {unassignedCount} line item{unassignedCount === 1 ? '' : 's'} unassigned - every line needs a vendor before you can confirm.
            </p>
          )}
          <div className="mb-3 flex flex-wrap gap-x-6 gap-y-1 text-xs text-text-secondary">
            {[...totalsByVendor.entries()].map(([vendorId, amount]) => (
              <span key={vendorId}>
                {rfxVendorByVendorId.get(vendorId)?.name}: {comparison.rows[0]?.cells && '₹'}
                {amount.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
              </span>
            ))}
          </div>
          <div className="mb-4 flex items-center justify-between">
            <span className="text-sm font-semibold text-text-primary">Grand total</span>
            <span className="text-lg font-semibold text-text-primary">
              ₹{grandTotal.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
            </span>
          </div>
          {error && <p className="mb-3 text-sm text-danger-text">{error}</p>}
          <Button
            className="w-full justify-center"
            onClick={handleConfirm}
            disabled={submitting || unassignedCount > 0}
          >
            {submitting ? 'Confirming award…' : 'Confirm award'}
          </Button>
        </div>
      </div>
    </div>
  )
}

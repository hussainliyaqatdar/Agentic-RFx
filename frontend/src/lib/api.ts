// In dev, Vite's server proxy rewrites '/api' to the local backend (see
// vite.config.ts). In production there's no such proxy, so a deployed build
// needs VITE_API_URL pointing straight at the backend's real origin.
const BASE_URL = import.meta.env.VITE_API_URL ?? '/api'

async function handle<T>(response: Response, path: string): Promise<T> {
  if (!response.ok) {
    const body = await response.text()
    throw new Error(`${response.status} ${path}: ${body}`)
  }
  return response.json() as Promise<T>
}

export async function apiGet<T>(path: string): Promise<T> {
  return handle<T>(await fetch(`${BASE_URL}${path}`), path)
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  return handle<T>(
    await fetch(`${BASE_URL}${path}`, {
      method: 'POST',
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    }),
    path,
  )
}

export interface RfxSummary {
  id: number
  title: string
  category: string
  status: string
  line_item_count: number
  vendor_count: number
  created_at: string
}

export interface RfxLineItem {
  id: number
  line_no: number
  sku_code: string
  description: string
  spec_attributes: {
    summary?: string
    ply?: number
    flute?: string
    dimensions_mm?: string
    gsm?: number
    printed?: boolean
  }
  quantity: number
  unit: string
}

export interface RfxQuestion {
  id: number
  question_no: number
  question_text: string
  question_type: string
  required: boolean
}

export interface RfxVendorSummary {
  id: number
  name: string
  response_status: string
  sent_at: string | null
}

export interface RfxDetail {
  id: number
  title: string
  category: string
  scope_description: string
  status: string
  canonical_currency: string
  payment_terms: string | null
  delivery_terms: string | null
  validity_days: number | null
  created_at: string
  line_items: RfxLineItem[]
  questions: RfxQuestion[]
  vendors: RfxVendorSummary[]
}

export interface DraftLineItem {
  sku_code: string | null
  is_new_sku: boolean
  description: string
  spec_summary: string
  quantity: number
  unit: string
}

export interface DraftQuestion {
  question_no: number | null
  question_text: string
  question_type: string
}

export interface RfxDraft {
  title: string | null
  category: string | null
  scope_description: string | null
  line_items: DraftLineItem[]
  questions: DraftQuestion[]
  payment_terms: string | null
  delivery_terms: string | null
  validity_days: number | null
}

export interface CopilotTurnResponse {
  session_id: number
  reply: string
  draft: RfxDraft
  ready_to_finalize: boolean
}

export interface ComparisonVendorColumn {
  rfx_vendor_id: number
  vendor_id: number
  name: string
  response_status: string
}

export interface ComparisonCell {
  unit_price_normalized: number | null
  currency_normalized: string | null
  extraction_confidence: number | null
  match_confidence: number | null
  needs_review: boolean
  conversion_notes: string | null
  source_citation: string | null
  vendor_raw_description: string | null
  lead_time_days: number | null
  evaluator_verdict: string | null
  evaluator_reasoning: string | null
}

export interface ComparisonRow {
  line_item_id: number
  line_no: number
  sku_code: string
  description: string
  spec_attributes: {
    summary?: string
    ply?: number
    flute?: string
    dimensions_mm?: string
    gsm?: number
    printed?: boolean
  }
  quantity: number
  unit: string
  cells: Record<string, ComparisonCell | null>
}

export interface ComparisonData {
  vendors: ComparisonVendorColumn[]
  rows: ComparisonRow[]
}

export interface VendorDetailAnswer {
  question_no: number
  question_text: string
  answer_text: string | null
  confidence: number | null
  needs_review: boolean | null
  evaluator_verdict: string | null
}

export interface VendorDetailDocument {
  id: number
  file_name: string
  document_type: string
}

export interface VendorDetail {
  vendor: { id: number; name: string; contact_email: string }
  response_status: string
  answers: VendorDetailAnswer[]
  documents: VendorDetailDocument[]
}

export interface ProposedAwardLine {
  sku_code: string
  vendor_id: number
  vendor_name: string
  reason: string
}

export interface ComputedTotal {
  total_amount: number
  currency: string
  line_count: number
  vendor_count: number
  unpriceable_skus: string[]
}

export interface AnalystTurnResponse {
  session_id: number
  reply: string
  proposed_award: ProposedAwardLine[]
  confidence_note: string | null
  computed_total: ComputedTotal | null
}

export const rfxApi = {
  list: () => apiGet<RfxSummary[]>('/rfx'),
  get: (id: number) => apiGet<RfxDetail>(`/rfx/${id}`),
  send: (id: number) => apiPost<{ status: string; vendor_count: number }>(`/rfx/${id}/send`),
  copilotTurn: (sessionId: number | null, message: string) =>
    apiPost<CopilotTurnResponse>('/copilot/turn', { session_id: sessionId, message }),
  finalize: (sessionId: number) => apiPost<{ rfx_id: number }>(`/copilot/${sessionId}/finalize`),
  extract: (id: number) => apiPost<{ vendors_processed: number; detail: unknown[] }>(`/rfx/${id}/extract`),
  comparison: (id: number) => apiGet<ComparisonData>(`/rfx/${id}/comparison`),
  vendorDetail: (rfxId: number, vendorId: number) => apiGet<VendorDetail>(`/rfx/${rfxId}/vendors/${vendorId}/detail`),
  documentDownloadUrl: (rfxId: number, documentId: number) => `${BASE_URL}/rfx/${rfxId}/documents/${documentId}/download`,
  analystTurn: (rfxId: number, sessionId: number | null, message: string) =>
    apiPost<AnalystTurnResponse>(`/rfx/${rfxId}/analyst/turn`, { session_id: sessionId, message }),
  award: (rfxId: number, awards: Record<string, number>) =>
    apiPost<{ status: string; line_items_awarded: number }>(`/rfx/${rfxId}/award`, { awards }),
}

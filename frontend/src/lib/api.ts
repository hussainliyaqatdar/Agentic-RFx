const BASE_URL = '/api'

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
  spec_attributes: { summary?: string }
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

export const rfxApi = {
  list: () => apiGet<RfxSummary[]>('/rfx'),
  get: (id: number) => apiGet<RfxDetail>(`/rfx/${id}`),
  send: (id: number) => apiPost<{ status: string; vendor_count: number }>(`/rfx/${id}/send`),
  copilotTurn: (sessionId: number | null, message: string) =>
    apiPost<CopilotTurnResponse>('/copilot/turn', { session_id: sessionId, message }),
  finalize: (sessionId: number) => apiPost<{ rfx_id: number }>(`/copilot/${sessionId}/finalize`),
}

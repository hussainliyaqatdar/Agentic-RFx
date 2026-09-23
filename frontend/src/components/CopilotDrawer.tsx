import { useState } from 'react'
import { rfxApi, type RfxDraft } from '../lib/api'
import { Button, IconButton } from './Button'
import { SendIcon, SparkleIcon, XIcon } from './icons'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

interface Props {
  onClose: () => void
  onFinalized: (rfxId: number) => void
}

const STARTER_PROMPTS = [
  'I need to source packaging for our fulfilment centres - the usual mix of standard 3-ply and 5-ply boxes, plus some retail-ready trays.',
  'Set up the standard quality questionnaire - certifications, defect rates, the Amazon packaging audit, the usual.',
  'Add 500 units of a heavy-duty 9-ply export carton, 700x600x600mm - we don’t carry this yet.',
]

export function CopilotDrawer({ onClose, onFinalized }: Props) {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', content: "Tell me what you need to source, and I'll draft the RFx as we go - line items, questionnaire, and terms." },
  ])
  const [draft, setDraft] = useState<RfxDraft | null>(null)
  const [sessionId, setSessionId] = useState<number | null>(null)
  const [readyToFinalize, setReadyToFinalize] = useState(false)
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [finalizing, setFinalizing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function send(message: string) {
    if (!message.trim() || sending) return
    setError(null)
    setMessages((prev) => [...prev, { role: 'user', content: message }])
    setInput('')
    setSending(true)
    try {
      const result = await rfxApi.copilotTurn(sessionId, message)
      setSessionId(result.session_id)
      setDraft(result.draft)
      setReadyToFinalize(result.ready_to_finalize)
      setMessages((prev) => [...prev, { role: 'assistant', content: result.reply }])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
    } finally {
      setSending(false)
    }
  }

  async function finalize() {
    if (!sessionId) return
    setFinalizing(true)
    setError(null)
    try {
      const { rfx_id } = await rfxApi.finalize(sessionId)
      onFinalized(rfx_id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not finalize the draft')
    } finally {
      setFinalizing(false)
    }
  }

  return (
    <div className="fixed inset-0 z-40 flex justify-end">
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />
      <div className="relative flex h-full w-full max-w-md flex-col bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-border-default px-5 py-4">
          <div className="flex items-center gap-2">
            <SparkleIcon className="text-brand-blue" />
            <span className="font-semibold text-text-primary">Agentic RFx co-pilot</span>
          </div>
          <IconButton onClick={onClose} aria-label="Close">
            <XIcon width={16} height={16} />
          </IconButton>
        </div>

        <div className="flex-1 space-y-3 overflow-y-auto px-5 py-4">
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div
                className={`max-w-[85%] rounded-2xl px-3.5 py-2 text-sm ${
                  m.role === 'user'
                    ? 'rounded-br-sm bg-brand-blue text-white'
                    : 'rounded-bl-sm bg-bg-hover text-text-primary'
                }`}
              >
                {m.content}
              </div>
            </div>
          ))}
          {sending && (
            <div className="flex justify-start">
              <div className="rounded-2xl rounded-bl-sm bg-bg-hover px-3.5 py-2 text-sm text-text-tertiary">
                Drafting…
              </div>
            </div>
          )}
        </div>

        {draft && (draft.line_items.length > 0 || draft.questions.length > 0) && (
          <div className="border-t border-border-default bg-bg-page px-5 py-3">
            <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-text-secondary">Draft so far</p>
            <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-text-secondary">
              <span>{draft.line_items.length} line item{draft.line_items.length === 1 ? '' : 's'}</span>
              <span>{draft.questions.length} questionnaire question{draft.questions.length === 1 ? '' : 's'}</span>
              {draft.line_items.some((li) => li.is_new_sku) && (
                <span className="text-warning-text">
                  {draft.line_items.filter((li) => li.is_new_sku).length} new item(s) not yet in catalog
                </span>
              )}
            </div>
          </div>
        )}

        {messages.length <= 1 && (
          <div className="border-t border-border-default px-5 py-3">
            <p className="mb-2 text-xs font-medium text-text-tertiary">Try one of these</p>
            <div className="flex flex-col gap-1.5">
              {STARTER_PROMPTS.map((p) => (
                <button
                  key={p}
                  onClick={() => send(p)}
                  className="rounded-lg border border-border-default px-3 py-2 text-left text-xs text-text-secondary hover:bg-bg-hover"
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        )}

        {error && <p className="px-5 pt-2 text-xs text-danger-text">{error}</p>}

        <div className="border-t border-border-default p-4">
          {readyToFinalize && (
            <Button className="mb-3 w-full justify-center" onClick={finalize} disabled={finalizing}>
              {finalizing ? 'Creating RFx…' : 'Finalize & create RFx'}
            </Button>
          )}
          <div className="flex items-center gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && send(input)}
              placeholder="Describe what you need…"
              className="flex-1 rounded-lg border border-border-strong px-3 py-2 text-sm outline-none focus:border-brand-blue"
            />
            <IconButton onClick={() => send(input)} disabled={sending} aria-label="Send">
              <SendIcon width={16} height={16} />
            </IconButton>
          </div>
        </div>
      </div>
    </div>
  )
}

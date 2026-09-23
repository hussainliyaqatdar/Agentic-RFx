import { useState } from 'react'
import { rfxApi, type ProposedAwardLine } from '../lib/api'
import { Button, IconButton } from './Button'
import { AlertTriangleIcon, SendIcon, SparkleIcon, XIcon } from './icons'

interface Message {
  role: 'user' | 'assistant'
  content: string
  proposedAward?: ProposedAwardLine[]
  confidenceNote?: string | null
  computedTotal?: { total_amount: number; currency: string; line_count: number; vendor_count: number } | null
}

interface Props {
  rfxId: number
  onClose: () => void
  onApplyAward: (awards: ProposedAwardLine[]) => void
}

const STARTER_PROMPTS = [
  'Which vendor is cheapest for the 3-ply boxes versus the 5-ply boxes?',
  'Has any vendor failed to answer whether they are ISO certified?',
  'Propose a split award, cheapest per line, only among vendors who cleared the quality questionnaire.',
]

export function AnalystChatDrawer({ rfxId, onClose, onApplyAward }: Props) {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', content: "Ask me anything about the quotes and questionnaire answers received - I'll only answer from what's actually in the data, and I'll say so if something isn't there." },
  ])
  const [sessionId, setSessionId] = useState<number | null>(null)
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function send(message: string) {
    if (!message.trim() || sending) return
    setError(null)
    setMessages((prev) => [...prev, { role: 'user', content: message }])
    setInput('')
    setSending(true)
    try {
      const result = await rfxApi.analystTurn(rfxId, sessionId, message)
      setSessionId(result.session_id)
      setMessages((prev) => [...prev, {
        role: 'assistant',
        content: result.reply,
        proposedAward: result.proposed_award.length ? result.proposed_award : undefined,
        confidenceNote: result.confidence_note,
        computedTotal: result.computed_total,
      }])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="fixed inset-0 z-40 flex justify-end">
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />
      <div className="relative flex h-full w-full max-w-md flex-col bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-border-default px-5 py-4">
          <div className="flex items-center gap-2">
            <SparkleIcon className="text-brand-blue" />
            <span className="font-semibold text-text-primary">Analyst chat</span>
          </div>
          <IconButton onClick={onClose} aria-label="Close">
            <XIcon width={16} height={16} />
          </IconButton>
        </div>

        <div className="flex-1 space-y-3 overflow-y-auto px-5 py-4">
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[90%] ${m.role === 'user' ? '' : 'w-full'}`}>
                <div
                  className={`rounded-2xl px-3.5 py-2 text-sm ${
                    m.role === 'user' ? 'rounded-br-sm bg-brand-blue text-white' : 'rounded-bl-sm bg-bg-hover text-text-primary'
                  }`}
                >
                  {m.content}
                </div>

                {m.confidenceNote && (
                  <div className="mt-1.5 flex items-start gap-1.5 rounded-lg bg-warning-bg px-3 py-2 text-xs text-warning-text">
                    <AlertTriangleIcon width={13} height={13} className="mt-0.5 shrink-0" />
                    <span>{m.confidenceNote}</span>
                  </div>
                )}

                {m.proposedAward && (
                  <div className="mt-1.5 rounded-lg border border-border-default bg-white p-3">
                    <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-text-secondary">
                      Proposed award ({m.proposedAward.length} line{m.proposedAward.length === 1 ? '' : 's'})
                    </p>
                    <ul className="mb-2 space-y-1 text-xs text-text-secondary">
                      {m.proposedAward.map((p) => (
                        <li key={p.sku_code}>
                          <span className="font-mono text-text-tertiary">{p.sku_code}</span> → {p.vendor_name}
                        </li>
                      ))}
                    </ul>
                    {m.computedTotal && (
                      <p className="mb-2 text-sm font-medium text-text-primary">
                        Computed total: {m.computedTotal.currency} {m.computedTotal.total_amount.toLocaleString('en-IN')}
                        <span className="ml-1 font-normal text-text-tertiary">
                          ({m.computedTotal.line_count} lines, {m.computedTotal.vendor_count} vendor{m.computedTotal.vendor_count === 1 ? '' : 's'})
                        </span>
                      </p>
                    )}
                    <Button className="w-full justify-center text-xs" onClick={() => onApplyAward(m.proposedAward!)}>
                      Apply to award panel
                    </Button>
                  </div>
                )}
              </div>
            </div>
          ))}
          {sending && (
            <div className="flex justify-start">
              <div className="rounded-2xl rounded-bl-sm bg-bg-hover px-3.5 py-2 text-sm text-text-tertiary">Thinking…</div>
            </div>
          )}
        </div>

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
          <div className="flex items-center gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && send(input)}
              placeholder="Ask about the responses…"
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

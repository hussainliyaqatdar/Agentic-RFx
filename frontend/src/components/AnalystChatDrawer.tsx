import { useEffect, useRef, useState } from 'react'
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

const GREETING: Message = {
  role: 'assistant',
  content: "Ask me anything about the quotes and questionnaire answers received - I'll only answer from what's actually in the data, and I'll say so if something isn't there.",
}

const STARTER_PROMPTS = [
  'Which vendor is cheapest for the 3-ply boxes versus the 5-ply boxes?',
  'Has any vendor failed to answer whether they are ISO certified?',
  'Propose a split award, cheapest per line, only among vendors who cleared the quality questionnaire.',
]

const MAX_TEXTAREA_HEIGHT = 160

export function AnalystChatDrawer({ rfxId, onClose, onApplyAward }: Props) {
  const [resuming, setResuming] = useState(true)
  const [messages, setMessages] = useState<Message[]>([GREETING])
  const [sessionId, setSessionId] = useState<number | null>(null)
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    rfxApi
      .latestAnalystSession(rfxId)
      .then((resumed) => {
        if (resumed && resumed.messages.length > 0) {
          setSessionId(resumed.session_id)
          setMessages(resumed.messages)
        }
      })
      .catch(() => {
        // Best-effort - fall back to a fresh conversation on any error.
      })
      .finally(() => setResuming(false))
  }, [rfxId])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ block: 'end' })
  }, [messages, resuming])

  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, MAX_TEXTAREA_HEIGHT)}px`
  }, [input])

  function startNewConversation() {
    setSessionId(null)
    setMessages([GREETING])
    setError(null)
  }

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
            <span className="font-semibold text-text-primary">RFx Analyst</span>
          </div>
          <div className="flex items-center gap-3">
            {sessionId != null && (
              <button onClick={startNewConversation} className="text-xs font-medium text-brand-blue hover:underline">
                New conversation
              </button>
            )}
            <IconButton onClick={onClose} aria-label="Close">
              <XIcon width={16} height={16} />
            </IconButton>
          </div>
        </div>

        <div className="flex-1 space-y-3 overflow-y-auto px-5 py-4">
          {resuming ? (
            <p className="text-sm text-text-secondary">Loading…</p>
          ) : (
            <>
              {messages.map((m, i) => (
                <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[90%] ${m.role === 'user' ? '' : 'w-full'}`}>
                    <div
                      className={`whitespace-pre-wrap rounded-2xl px-3.5 py-2 text-sm ${
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
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {!resuming && messages.length <= 1 && (
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
          <div className="flex items-end gap-2">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  send(input)
                }
              }}
              placeholder="Ask about the responses… (Shift+Enter for a new line)"
              rows={1}
              style={{ maxHeight: MAX_TEXTAREA_HEIGHT }}
              className="flex-1 resize-none rounded-lg border border-border-strong px-3 py-2 text-sm outline-none focus:border-brand-blue"
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

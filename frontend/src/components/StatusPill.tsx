type Tone = 'success' | 'warning' | 'danger' | 'info' | 'neutral'

const TONE_CLASSES: Record<Tone, string> = {
  success: 'bg-success-bg text-success-text',
  warning: 'bg-warning-bg text-warning-text',
  danger: 'bg-danger-bg text-danger-text',
  info: 'bg-info-bg text-info-text',
  neutral: 'bg-border-default text-text-secondary',
}

const STATUS_TONE: Record<string, Tone> = {
  draft: 'info',
  pending_approval: 'warning',
  sent: 'warning',
  responses_in: 'warning',
  awarded: 'success',
  closed: 'neutral',
}

export function StatusPill({ tone, children }: { tone: Tone; children: React.ReactNode }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${TONE_CLASSES[tone]}`}>
      {children}
    </span>
  )
}

export function RfxStatusPill({ status }: { status: string }) {
  const tone = STATUS_TONE[status] ?? 'neutral'
  return <StatusPill tone={tone}>{status.replace(/_/g, ' ')}</StatusPill>
}

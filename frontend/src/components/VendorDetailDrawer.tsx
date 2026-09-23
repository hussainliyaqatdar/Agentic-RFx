import { useEffect, useState } from 'react'
import { rfxApi, type VendorDetail } from '../lib/api'
import { IconButton } from './Button'
import { DocumentIcon, PaperclipIcon, XIcon } from './icons'

interface Props {
  rfxId: number
  vendorId: number
  onClose: () => void
}

export function VendorDetailDrawer({ rfxId, vendorId, onClose }: Props) {
  const [detail, setDetail] = useState<VendorDetail | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    rfxApi
      .vendorDetail(rfxId, vendorId)
      .then(setDetail)
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load'))
  }, [rfxId, vendorId])

  return (
    <div className="fixed inset-0 z-40 flex justify-end">
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />
      <div className="relative flex h-full w-full max-w-md flex-col overflow-y-auto bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-border-default px-5 py-4">
          <span className="font-semibold text-text-primary">{detail?.vendor.name ?? 'Vendor details'}</span>
          <IconButton onClick={onClose} aria-label="Close">
            <XIcon width={16} height={16} />
          </IconButton>
        </div>

        {error && <p className="px-5 pt-4 text-sm text-danger-text">{error}</p>}
        {!detail && !error && <p className="px-5 pt-4 text-sm text-text-secondary">Loading…</p>}

        {detail && (
          <div className="space-y-6 px-5 py-5">
            <section>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-text-secondary">
                Attachments ({detail.documents.length})
              </p>
              <div className="space-y-1.5">
                {detail.documents.map((doc) => (
                  <a
                    key={doc.id}
                    href={rfxApi.documentDownloadUrl(rfxId, doc.id)}
                    download
                    className="flex items-center gap-2 rounded-lg border border-border-default px-3 py-2 text-sm text-text-primary hover:bg-bg-hover"
                  >
                    {doc.document_type === 'email_text' ? (
                      <PaperclipIcon width={15} height={15} className="text-text-tertiary" />
                    ) : (
                      <DocumentIcon width={15} height={15} className="text-text-tertiary" />
                    )}
                    <span className="flex-1">{doc.file_name}</span>
                    <span className="text-xs text-text-tertiary">{doc.document_type}</span>
                  </a>
                ))}
                {detail.documents.length === 0 && (
                  <p className="text-sm text-text-tertiary">No documents on file.</p>
                )}
              </div>
            </section>

            <section>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-text-secondary">
                Quality questionnaire
              </p>
              <div className="space-y-2">
                {detail.answers.map((a) => (
                  <div key={a.question_no} className="rounded-lg border border-border-default px-3 py-2.5">
                    <p className="text-xs text-text-secondary">
                      {a.question_no}. {a.question_text}
                    </p>
                    {a.answer_text ? (
                      <p className="mt-1 text-sm text-text-primary">
                        {a.answer_text}
                        {a.needs_review && (
                          <span className="ml-2 rounded bg-warning-bg px-1.5 py-0.5 text-xs text-warning-text">
                            review
                          </span>
                        )}
                      </p>
                    ) : (
                      <p className="mt-1 text-sm italic text-text-tertiary">Not answered</p>
                    )}
                  </div>
                ))}
              </div>
            </section>
          </div>
        )}
      </div>
    </div>
  )
}

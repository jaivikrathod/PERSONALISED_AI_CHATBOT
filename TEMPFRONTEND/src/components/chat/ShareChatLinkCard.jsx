import { useCallback, useState } from 'react'
import {
  ArrowTopRightOnSquareIcon,
  CheckIcon,
  ClipboardIcon,
  LinkIcon,
} from '@heroicons/react/24/outline'
import Button from '../ui/Button'

/**
 * The shareable public chatbot URL for a company.
 *
 * `/chat/:companyId` needs no login, so this is the link a company hands to
 * customers, drops in an email footer or embeds in an iframe. Shown to
 * Admins/Managers only — agents answer from the console instead.
 */
export default function ShareChatLinkCard({ companyId }) {
  const [copied, setCopied] = useState(false)

  const url = companyId ? `${window.location.origin}/chat/${companyId}` : ''

  const copy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(url)
    } catch {
      // Clipboard API needs a secure context; fall back to a manual select.
      window.prompt('Copy this chat link:', url)
      return
    }
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }, [url])

  if (!companyId) return null

  return (
    <div className="mb-5 rounded-xl border border-brand-100 bg-brand-50/60 p-4 dark:border-brand-500/20 dark:bg-brand-500/5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-white text-brand-600 shadow-sm dark:bg-gray-900 dark:text-brand-300">
          <LinkIcon className="h-5 w-5" />
        </span>

        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">
            Your public chat link
          </p>
          <p className="truncate font-mono text-xs text-gray-600 dark:text-gray-400">
            {url}
          </p>
        </div>

        <div className="flex shrink-0 gap-2">
          <Button variant="secondary" size="sm" onClick={copy}>
            {copied ? (
              <CheckIcon className="h-4 w-4 text-emerald-600" />
            ) : (
              <ClipboardIcon className="h-4 w-4" />
            )}
            {copied ? 'Copied' : 'Copy'}
          </Button>
          <Button
            as="a"
            variant="ghost"
            size="sm"
            href={url}
            target="_blank"
            rel="noreferrer"
          >
            <ArrowTopRightOnSquareIcon className="h-4 w-4" />
            Open
          </Button>
        </div>
      </div>

      <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
        Anyone with this link can chat — no account needed. Questions the
        assistant can&rsquo;t answer are handed to an available agent.
      </p>
    </div>
  )
}

import { useState } from 'react'
import { useDispatch } from 'react-redux'
import {
  CheckIcon,
  ClipboardDocumentIcon,
  CodeBracketIcon,
} from '@heroicons/react/24/outline'
import { Modal, Button } from '../../components/ui'
import { addToast } from '../../redux/slices/uiSlice'
import { WIDGET_DOMAIN } from '../../utils/constants'

export default function WidgetScriptModal({ open, onClose, chatbot }) {
  const dispatch = useDispatch()
  const [copied, setCopied] = useState(false)

  const token = chatbot?.widget_token || 'YOUR_WIDGET_TOKEN'
  const snippet = `<script src="${WIDGET_DOMAIN}/widget.js"></script>
<script>
  Chatbot.init({
    token: "${token}"
  });
</script>`

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(snippet)
      setCopied(true)
      dispatch(addToast({ type: 'success', message: 'Widget script copied to clipboard.' }))
      setTimeout(() => setCopied(false), 2000)
    } catch {
      dispatch(addToast({ type: 'error', message: 'Could not copy. Select and copy manually.' }))
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      size="lg"
      title="Install widget"
      description={`Add ${chatbot?.name || 'your chatbot'} to any website.`}
      footer={
        <Button onClick={onClose} variant="secondary">
          Done
        </Button>
      }
    >
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
          <CodeBracketIcon className="h-5 w-5 text-brand-500" />
          Paste this snippet just before the closing{' '}
          <code className="rounded bg-gray-100 px-1.5 py-0.5 text-xs dark:bg-gray-800">
            &lt;/body&gt;
          </code>{' '}
          tag.
        </div>

        <div className="relative">
          <pre className="overflow-x-auto rounded-xl bg-gray-900 p-4 text-sm leading-relaxed text-gray-100 dark:bg-gray-950 dark:ring-1 dark:ring-gray-800">
            <code>{snippet}</code>
          </pre>
          <button
            onClick={copy}
            className="absolute right-3 top-3 inline-flex items-center gap-1.5 rounded-lg bg-white/10 px-2.5 py-1.5 text-xs font-medium text-white backdrop-blur transition hover:bg-white/20"
          >
            {copied ? (
              <>
                <CheckIcon className="h-4 w-4 text-emerald-400" /> Copied
              </>
            ) : (
              <>
                <ClipboardDocumentIcon className="h-4 w-4" /> Copy
              </>
            )}
          </button>
        </div>

        <div className="rounded-lg border border-gray-200 px-4 py-3 dark:border-gray-700">
          <p className="text-xs font-medium uppercase tracking-wide text-gray-400">
            Widget Token
          </p>
          <p className="mt-1 font-mono text-sm text-gray-700 dark:text-gray-200">{token}</p>
        </div>
      </div>
    </Modal>
  )
}

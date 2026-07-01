import { ExclamationTriangleIcon } from '@heroicons/react/24/outline'
import Modal from './Modal'
import Button from './Button'

/** Confirmation modal for destructive actions. */
export default function ConfirmDialog({
  open,
  onClose,
  onConfirm,
  title = 'Are you sure?',
  description,
  confirmLabel = 'Confirm',
  loading = false,
  danger = true,
}) {
  return (
    <Modal
      open={open}
      onClose={onClose}
      title={title}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <Button variant={danger ? 'danger' : 'primary'} onClick={onConfirm} loading={loading}>
            {confirmLabel}
          </Button>
        </>
      }
    >
      <div className="flex gap-4">
        {danger && (
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-red-100 text-red-600 dark:bg-red-500/15">
            <ExclamationTriangleIcon className="h-5 w-5" />
          </span>
        )}
        <p className="text-sm text-gray-600 dark:text-gray-300">{description}</p>
      </div>
    </Modal>
  )
}

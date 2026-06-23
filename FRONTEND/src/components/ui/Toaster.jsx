import { useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import {
  CheckCircleIcon,
  ExclamationCircleIcon,
  InformationCircleIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline'
import { removeToast } from '../../redux/slices/uiSlice'
import { cn } from '../../utils/cn'

const ICONS = {
  success: CheckCircleIcon,
  error: ExclamationCircleIcon,
  info: InformationCircleIcon,
}
const TONES = {
  success: 'text-emerald-500',
  error: 'text-red-500',
  info: 'text-brand-500',
}

function Toast({ toast }) {
  const dispatch = useDispatch()
  const Icon = ICONS[toast.type] || ICONS.info

  useEffect(() => {
    const t = setTimeout(() => dispatch(removeToast(toast.id)), 4000)
    return () => clearTimeout(t)
  }, [dispatch, toast.id])

  return (
    <div className="flex w-80 items-start gap-3 rounded-xl border border-gray-200 bg-white p-4 shadow-card-hover animate-slide-in-right dark:border-gray-800 dark:bg-gray-900">
      <Icon className={cn('h-5 w-5 shrink-0', TONES[toast.type])} />
      <p className="flex-1 text-sm text-gray-700 dark:text-gray-200">{toast.message}</p>
      <button
        onClick={() => dispatch(removeToast(toast.id))}
        className="text-gray-400 hover:text-gray-600"
      >
        <XMarkIcon className="h-4 w-4" />
      </button>
    </div>
  )
}

export default function Toaster() {
  const toasts = useSelector((s) => s.ui.toasts)
  return (
    <div className="fixed bottom-4 right-4 z-[60] flex flex-col gap-2">
      {toasts.map((t) => (
        <Toast key={t.id} toast={t} />
      ))}
    </div>
  )
}

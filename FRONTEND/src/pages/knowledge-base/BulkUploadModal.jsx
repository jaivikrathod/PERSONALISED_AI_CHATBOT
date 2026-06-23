import { useRef, useState } from 'react'
import { useDispatch } from 'react-redux'
import {
  ArrowUpTrayIcon,
  DocumentTextIcon,
  TableCellsIcon,
} from '@heroicons/react/24/outline'
import { Modal, Button } from '../../components/ui'
import { addToast } from '../../redux/slices/uiSlice'
import { bulkUploadFaqs, fetchFaqs } from '../../redux/slices/knowledgeBaseSlice'
import { cn } from '../../utils/cn'

const ACCEPT = '.csv,.xlsx,.xls'

export default function BulkUploadModal({ open, onClose }) {
  const dispatch = useDispatch()
  const inputRef = useRef(null)
  const [file, setFile] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)

  const reset = () => {
    setFile(null)
    setUploading(false)
  }

  const handleClose = () => {
    reset()
    onClose()
  }

  const pick = (f) => {
    if (!f) return
    const ok = /\.(csv|xlsx|xls)$/i.test(f.name)
    if (!ok) {
      dispatch(addToast({ type: 'error', message: 'Please upload a CSV or Excel file.' }))
      return
    }
    setFile(f)
  }

  const onDrop = (e) => {
    e.preventDefault()
    setDragging(false)
    pick(e.dataTransfer.files?.[0])
  }

  const upload = async () => {
    if (!file) return
    setUploading(true)
    const result = await dispatch(bulkUploadFaqs(file))
    setUploading(false)
    if (bulkUploadFaqs.fulfilled.match(result)) {
      dispatch(addToast({ type: 'success', message: 'FAQs imported successfully.' }))
      dispatch(fetchFaqs())
      handleClose()
    } else {
      dispatch(addToast({ type: 'error', message: result.payload || 'Upload failed.' }))
    }
  }

  const isExcel = file && /\.(xlsx|xls)$/i.test(file.name)

  return (
    <Modal
      open={open}
      onClose={handleClose}
      title="Bulk upload FAQs"
      description="Import many questions at once from a CSV or Excel file."
      footer={
        <>
          <Button variant="secondary" onClick={handleClose} disabled={uploading}>
            Cancel
          </Button>
          <Button onClick={upload} loading={uploading} disabled={!file}>
            Import
          </Button>
        </>
      }
    >
      <div
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={cn(
          'flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-10 text-center transition',
          dragging
            ? 'border-brand-500 bg-brand-50 dark:bg-brand-500/10'
            : 'border-gray-300 hover:border-brand-400 dark:border-gray-700',
        )}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT}
          className="hidden"
          onChange={(e) => pick(e.target.files?.[0])}
        />
        {file ? (
          <div className="flex items-center gap-3">
            {isExcel ? (
              <TableCellsIcon className="h-8 w-8 text-emerald-500" />
            ) : (
              <DocumentTextIcon className="h-8 w-8 text-brand-500" />
            )}
            <div className="text-left">
              <p className="text-sm font-medium text-gray-800 dark:text-gray-100">
                {file.name}
              </p>
              <p className="text-xs text-gray-400">
                {(file.size / 1024).toFixed(1)} KB · click to replace
              </p>
            </div>
          </div>
        ) : (
          <>
            <ArrowUpTrayIcon className="h-9 w-9 text-gray-400" />
            <p className="mt-3 text-sm font-medium text-gray-700 dark:text-gray-200">
              Drag & drop or <span className="text-brand-600">browse</span>
            </p>
            <p className="mt-1 text-xs text-gray-400">CSV, XLSX or XLS — up to 5MB</p>
          </>
        )}
      </div>

      <div className="mt-4 rounded-lg bg-gray-50 px-4 py-3 text-xs text-gray-500 dark:bg-gray-800/60 dark:text-gray-400">
        <p className="font-medium text-gray-600 dark:text-gray-300">Expected columns:</p>
        <p className="mt-1">
          <code className="rounded bg-gray-200 px-1.5 py-0.5 dark:bg-gray-700">question</code>{' '}
          and{' '}
          <code className="rounded bg-gray-200 px-1.5 py-0.5 dark:bg-gray-700">answer</code>
        </p>
      </div>
    </Modal>
  )
}

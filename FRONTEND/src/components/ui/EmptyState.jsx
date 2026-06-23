import { InboxIcon } from '@heroicons/react/24/outline'

export default function EmptyState({ title, description, icon: Icon = InboxIcon, action }) {
  return (
    <div className="flex flex-col items-center justify-center py-6 text-center">
      <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-gray-100 text-gray-400 dark:bg-gray-800">
        <Icon className="h-6 w-6" />
      </div>
      <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{title}</p>
      {description && (
        <p className="mt-1 max-w-sm text-sm text-gray-500 dark:text-gray-400">
          {description}
        </p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

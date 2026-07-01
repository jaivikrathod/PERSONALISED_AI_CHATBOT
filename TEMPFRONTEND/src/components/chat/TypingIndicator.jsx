import Avatar from '../ui/Avatar'

/** Three-dot "is typing" bubble. */
export default function TypingIndicator({ name = 'Customer' }) {
  return (
    <div className="flex items-end gap-2">
      <Avatar name={name} size="sm" />
      <div className="flex items-center gap-1 rounded-2xl rounded-bl-md bg-white px-4 py-3 shadow-sm ring-1 ring-gray-200 dark:bg-gray-800 dark:ring-gray-700">
        {[0, 150, 300].map((d) => (
          <span
            key={d}
            className="h-2 w-2 animate-bounce rounded-full bg-gray-400"
            style={{ animationDelay: `${d}ms` }}
          />
        ))}
      </div>
    </div>
  )
}

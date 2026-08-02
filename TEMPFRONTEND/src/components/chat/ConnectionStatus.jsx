import { SOCKET_STATUS } from '../../utils/constants'
import { cn } from '../../utils/cn'

const STATES = {
  [SOCKET_STATUS.CONNECTING]: { label: 'Connecting…', dot: 'bg-amber-400' },
  [SOCKET_STATUS.OPEN]: { label: 'Live', dot: 'bg-emerald-500' },
  [SOCKET_STATUS.CLOSED]: { label: 'Reconnecting…', dot: 'bg-red-500' },
}

/** Live WebSocket state pill, shared by the widget and the agent console. */
export default function ConnectionStatus({ status, className }) {
  const state = STATES[status] || STATES[SOCKET_STATUS.CONNECTING]
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400',
        className,
      )}
    >
      <span
        className={cn(
          'h-2 w-2 rounded-full',
          state.dot,
          status === SOCKET_STATUS.OPEN && 'animate-pulse',
        )}
      />
      {state.label}
    </span>
  )
}

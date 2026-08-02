import { useNavigate } from 'react-router-dom'
import { useDispatch } from 'react-redux'
import {
  ArrowRightOnRectangleIcon,
  BuildingOffice2Icon,
  ChevronDownIcon,
} from '@heroicons/react/24/outline'
import Dropdown from '../ui/Dropdown'
import Avatar from '../ui/Avatar'
import useAuth from '../../hooks/useAuth'
import { logout } from '../../redux/slices/authSlice'

export default function ProfileDropdown() {
  const { user, userType } = useAuth()
  const dispatch = useDispatch()
  const navigate = useNavigate()

  const name = user?.name || user?.email || 'User'

  const handleLogout = () => {
    dispatch(logout())
    navigate('/login', { replace: true })
  }

  return (
    <Dropdown
      trigger={
        <button className="flex items-center gap-2 rounded-lg p-1 pr-2 transition hover:bg-gray-100 dark:hover:bg-gray-800">
          <Avatar name={name} size="sm" />
          <span className="hidden text-left sm:block">
            <span className="block text-sm font-medium leading-tight text-gray-800 dark:text-gray-100">
              {name}
            </span>
            <span className="block text-xs leading-tight text-gray-400">
              {userType || 'Member'}
            </span>
          </span>
          <ChevronDownIcon className="hidden h-4 w-4 text-gray-400 sm:block" />
        </button>
      }
    >
      <div className="border-b border-gray-100 px-3.5 py-3 dark:border-gray-800">
        <p className="text-sm font-medium text-gray-800 dark:text-gray-100">{name}</p>
        <p className="truncate text-xs text-gray-400">{user?.email}</p>
        {user?.company_name && (
          <p className="mt-2 flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
            <BuildingOffice2Icon className="h-4 w-4 shrink-0" />
            <span className="truncate">{user.company_name}</span>
          </p>
        )}
      </div>
      <Dropdown.Item icon={ArrowRightOnRectangleIcon} danger onClick={handleLogout}>
        Log out
      </Dropdown.Item>
    </Dropdown>
  )
}

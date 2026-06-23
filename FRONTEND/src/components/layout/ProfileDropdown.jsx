import { useNavigate } from 'react-router-dom'
import { useDispatch } from 'react-redux'
import {
  ChevronDownIcon,
  UserCircleIcon,
  Cog6ToothIcon,
  ArrowRightOnRectangleIcon,
} from '@heroicons/react/24/outline'
import Dropdown from '../ui/Dropdown'
import Avatar from '../ui/Avatar'
import useAuth from '../../hooks/useAuth'
import { logout } from '../../redux/slices/authSlice'

export default function ProfileDropdown() {
  const { user } = useAuth()
  const dispatch = useDispatch()
  const navigate = useNavigate()

  const name = user?.name || user?.full_name || user?.email || 'User'
  const email = user?.email || ''

  const handleLogout = async () => {
    await dispatch(logout())
    navigate('/login', { replace: true })
  }

  return (
    <Dropdown
      trigger={
        <button className="flex items-center gap-2 rounded-lg p-1 pr-2 transition hover:bg-gray-100 dark:hover:bg-gray-800">
          <Avatar name={name} src={user?.avatar} size="sm" />
          <span className="hidden text-left sm:block">
            <span className="block text-sm font-medium leading-tight text-gray-800 dark:text-gray-100">
              {name}
            </span>
            <span className="block text-xs leading-tight text-gray-400">
              {user?.role || 'Member'}
            </span>
          </span>
          <ChevronDownIcon className="hidden h-4 w-4 text-gray-400 sm:block" />
        </button>
      }
    >
      <div className="border-b border-gray-100 px-3.5 py-3 dark:border-gray-800">
        <p className="text-sm font-medium text-gray-800 dark:text-gray-100">{name}</p>
        <p className="truncate text-xs text-gray-400">{email}</p>
      </div>
      <Dropdown.Item icon={UserCircleIcon} onClick={() => navigate('/settings')}>
        Profile
      </Dropdown.Item>
      <Dropdown.Item icon={Cog6ToothIcon} onClick={() => navigate('/settings')}>
        Settings
      </Dropdown.Item>
      <Dropdown.Divider />
      <Dropdown.Item icon={ArrowRightOnRectangleIcon} danger onClick={handleLogout}>
        Sign out
      </Dropdown.Item>
    </Dropdown>
  )
}

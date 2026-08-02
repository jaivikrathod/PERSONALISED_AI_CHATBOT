import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { useDispatch } from 'react-redux'
import { Link, useNavigate } from 'react-router-dom'
import {
  BuildingOffice2Icon,
  EnvelopeIcon,
  LockClosedIcon,
  MapPinIcon,
  PhoneIcon,
  UserIcon,
} from '@heroicons/react/24/outline'
import { Button, Input, Select } from '../../components/ui'
import AuthLayout from './AuthLayout'
import useAuth from '../../hooks/useAuth'
import { clearAuthError, register as registerCompany } from '../../redux/slices/authSlice'
import { GENDER_OPTIONS } from '../../utils/constants'

function Section({ title, children }) {
  return (
    <div>
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
        {title}
      </h2>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">{children}</div>
    </div>
  )
}

/**
 * Step 1 of the flow: register a company and create its Admin user.
 * Two API calls happen under the hood (POST /companies/ then POST /users/).
 */
export default function RegisterPage() {
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const { isLoading, error } = useAuth()

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm()

  useEffect(() => () => dispatch(clearAuthError()), [dispatch])

  const onSubmit = async (values) => {
    const result = await dispatch(
      registerCompany({
        company: {
          name: values.company_name,
          email: values.company_email,
          mobile: values.company_mobile,
          address: values.company_address,
        },
        admin: {
          name: values.admin_name,
          email: values.admin_email,
          password: values.admin_password,
          gender: values.admin_gender,
          dob: values.admin_dob,
        },
      }),
    )

    if (registerCompany.fulfilled.match(result)) {
      // Send the new admin to the login screen with a success hint.
      navigate('/login', {
        state: { registered: true, email: values.admin_email },
        replace: true,
      })
    }
  }

  return (
    <AuthLayout
      title="Register your company"
      subtitle="Create a company and its Admin account to get started."
      width="max-w-xl"
    >
      {error && (
        <div
          role="alert"
          className="mt-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-400"
        >
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="mt-6 space-y-6" noValidate>
        <Section title="Company details">
          <Input
            label="Company name"
            placeholder="Acme Inc."
            icon={<BuildingOffice2Icon className="h-5 w-5" />}
            error={errors.company_name?.message}
            {...register('company_name', { required: 'Required' })}
          />
          <Input
            label="Company email"
            type="email"
            placeholder="hello@acme.com"
            icon={<EnvelopeIcon className="h-5 w-5" />}
            error={errors.company_email?.message}
            {...register('company_email', {
              required: 'Required',
              pattern: {
                value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
                message: 'Enter a valid email address',
              },
            })}
          />
          <Input
            label="Mobile"
            placeholder="+1 555 000 1234"
            icon={<PhoneIcon className="h-5 w-5" />}
            error={errors.company_mobile?.message}
            {...register('company_mobile', {
              required: 'Required',
              maxLength: { value: 15, message: 'At most 15 characters' },
            })}
          />
          <Input
            label="Address"
            placeholder="221B Baker Street, London"
            icon={<MapPinIcon className="h-5 w-5" />}
            error={errors.company_address?.message}
            {...register('company_address', { required: 'Required' })}
          />
        </Section>

        <Section title="Admin account">
          <Input
            label="Full name"
            placeholder="Jane Doe"
            icon={<UserIcon className="h-5 w-5" />}
            error={errors.admin_name?.message}
            {...register('admin_name', { required: 'Required' })}
          />
          <Input
            label="Email"
            type="email"
            placeholder="jane@acme.com"
            icon={<EnvelopeIcon className="h-5 w-5" />}
            autoComplete="username"
            error={errors.admin_email?.message}
            {...register('admin_email', {
              required: 'Required',
              pattern: {
                value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
                message: 'Enter a valid email address',
              },
            })}
          />
          <Input
            label="Password"
            type="password"
            placeholder="••••••••"
            icon={<LockClosedIcon className="h-5 w-5" />}
            autoComplete="new-password"
            error={errors.admin_password?.message}
            {...register('admin_password', {
              required: 'Required',
              minLength: { value: 6, message: 'Min 6 characters' },
            })}
          />
          <Select
            label="Gender"
            error={errors.admin_gender?.message}
            {...register('admin_gender', { required: 'Required' })}
          >
            <option value="">Select…</option>
            {GENDER_OPTIONS.map((g) => (
              <option key={g.value} value={g.value}>
                {g.label}
              </option>
            ))}
          </Select>
          <Input
            label="Date of birth"
            type="date"
            containerClassName="sm:col-span-2"
            error={errors.admin_dob?.message}
            {...register('admin_dob', { required: 'Required' })}
          />
        </Section>

        <Button type="submit" size="lg" className="w-full" loading={isLoading}>
          Create company &amp; admin
        </Button>
      </form>

      <p className="mt-8 text-center text-sm text-gray-500 dark:text-gray-400">
        Already have an account?{' '}
        <Link to="/login" className="font-medium text-brand-600 hover:underline">
          Log in
        </Link>
      </p>
    </AuthLayout>
  )
}

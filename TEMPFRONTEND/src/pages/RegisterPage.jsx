import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router-dom'
import { Button, Input, Select, Card, CardBody } from '../components/ui'
import { GENDER_OPTIONS } from '../utils/constants'
import { authService } from '../services/authService'

/**
 * Step 1 of the flow: register a company and create its Admin user.
 * Two API calls happen under the hood (POST /companies/ then POST /users/).
 */
export default function RegisterPage() {
  const navigate = useNavigate()
  const [serverError, setServerError] = useState('')
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm()

  const onSubmit = async (values) => {
    setServerError('')
    try {
      await authService.register({
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
      })
      // Send the new admin to the login screen with a success hint.
      navigate('/login', {
        state: { registered: true, email: values.admin_email },
      })
    } catch (err) {
      setServerError(err.message || 'Registration failed.')
    }
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center px-4 py-10">
      <div className="mb-6 text-center">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          Register your company
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Create a company and its Admin account to get started.
        </p>
      </div>

      <Card>
        <CardBody>
          {serverError && (
            <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-500/10 dark:text-red-400">
              {serverError}
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            {/* --- Company details --- */}
            <div>
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                Company details
              </h2>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <Input
                  label="Company name"
                  error={errors.company_name?.message}
                  {...register('company_name', { required: 'Required' })}
                />
                <Input
                  label="Company email"
                  type="email"
                  error={errors.company_email?.message}
                  {...register('company_email', { required: 'Required' })}
                />
                <Input
                  label="Mobile"
                  error={errors.company_mobile?.message}
                  {...register('company_mobile', { required: 'Required' })}
                />
                <Input
                  label="Address"
                  error={errors.company_address?.message}
                  {...register('company_address', { required: 'Required' })}
                />
              </div>
            </div>

            {/* --- Admin account --- */}
            <div>
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                Admin account
              </h2>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <Input
                  label="Full name"
                  error={errors.admin_name?.message}
                  {...register('admin_name', { required: 'Required' })}
                />
                <Input
                  label="Email"
                  type="email"
                  error={errors.admin_email?.message}
                  {...register('admin_email', { required: 'Required' })}
                />
                <Input
                  label="Password"
                  type="password"
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
              </div>
            </div>

            <Button type="submit" size="lg" loading={isSubmitting} className="w-full">
              Create company &amp; admin
            </Button>
          </form>

          <p className="mt-4 text-center text-sm text-gray-500 dark:text-gray-400">
            Already have an account?{' '}
            <Link to="/login" className="font-medium text-brand-600 hover:underline">
              Log in
            </Link>
          </p>
        </CardBody>
      </Card>
    </div>
  )
}

import { useEffect, useRef, useState } from 'react'
import { useForm, Controller } from 'react-hook-form'
import { useDispatch, useSelector } from 'react-redux'
import {
  BuildingOffice2Icon,
  PhotoIcon,
  SwatchIcon,
} from '@heroicons/react/24/outline'
import {
  PageHeader,
  Card,
  CardHeader,
  CardBody,
  Button,
  Input,
  Textarea,
  Toggle,
} from '../../components/ui'
import { addToast } from '../../redux/slices/uiSlice'
import { fetchSettings, saveSettings } from '../../redux/slices/settingsSlice'
import { mockSettings } from '../../utils/mockData'

const THEME_PRESETS = ['#6366f1', '#8b5cf6', '#0ea5e9', '#10b981', '#f59e0b', '#ef4444', '#ec4899']

export default function SettingsPage() {
  const dispatch = useDispatch()
  const { data, saving, status } = useSelector((s) => s.settings)
  const fileRef = useRef(null)
  const [logoPreview, setLogoPreview] = useState(null)

  const {
    register,
    handleSubmit,
    control,
    reset,
    setValue,
    watch,
    formState: { errors },
  } = useForm({ defaultValues: mockSettings })

  useEffect(() => {
    dispatch(fetchSettings())
  }, [dispatch])

  // Hydrate form once settings load (fall back to demo data).
  useEffect(() => {
    const s = data || mockSettings
    reset(s)
    setLogoPreview(typeof s.logo === 'string' ? s.logo : null)
  }, [data, reset])

  const themeColor = watch('theme_color')

  const onLogo = (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setValue('logo', file)
    setLogoPreview(URL.createObjectURL(file))
  }

  const onSubmit = async (values) => {
    const result = await dispatch(saveSettings(values))
    if (saveSettings.fulfilled.match(result)) {
      dispatch(addToast({ type: 'success', message: 'Settings saved.' }))
    } else {
      dispatch(addToast({ type: 'error', message: result.payload || 'Could not save settings.' }))
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <PageHeader title="Settings" subtitle="Configure your workspace and chat widget.">
        <Button type="submit" loading={saving || status === 'loading'}>
          Save Settings
        </Button>
      </PageHeader>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Company details */}
        <Card>
          <CardHeader
            title="Company Details"
            subtitle="Basic information about your organization."
          />
          <CardBody className="space-y-4">
            <Input
              label="Company name"
              icon={<BuildingOffice2Icon className="h-5 w-5" />}
              error={errors.company_name?.message}
              {...register('company_name', { required: 'Company name is required' })}
            />
            <Input
              label="Support email"
              type="email"
              {...register('support_email')}
            />

            {/* Logo upload */}
            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">
                Logo
              </label>
              <div className="flex items-center gap-4">
                <div className="flex h-16 w-16 items-center justify-center overflow-hidden rounded-xl border border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-800">
                  {logoPreview ? (
                    <img src={logoPreview} alt="Logo" className="h-full w-full object-cover" />
                  ) : (
                    <PhotoIcon className="h-7 w-7 text-gray-300" />
                  )}
                </div>
                <div>
                  <input
                    ref={fileRef}
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={onLogo}
                  />
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    onClick={() => fileRef.current?.click()}
                  >
                    Upload logo
                  </Button>
                  <p className="mt-1 text-xs text-gray-400">PNG or JPG, up to 2MB.</p>
                </div>
              </div>
            </div>
          </CardBody>
        </Card>

        {/* Theme */}
        <Card>
          <CardHeader title="Branding" subtitle="Customize how your widget looks." />
          <CardBody className="space-y-4">
            <div>
              <label className="mb-2 flex items-center gap-1.5 text-sm font-medium text-gray-700 dark:text-gray-300">
                <SwatchIcon className="h-4 w-4" /> Theme color
              </label>
              <div className="flex flex-wrap items-center gap-2">
                {THEME_PRESETS.map((c) => (
                  <button
                    key={c}
                    type="button"
                    onClick={() => setValue('theme_color', c)}
                    className="h-9 w-9 rounded-full ring-2 ring-offset-2 ring-offset-white transition dark:ring-offset-gray-900"
                    style={{
                      background: c,
                      boxShadow: themeColor === c ? `0 0 0 2px ${c}` : 'none',
                    }}
                    aria-label={c}
                  />
                ))}
                <Controller
                  control={control}
                  name="theme_color"
                  render={({ field }) => (
                    <input
                      type="color"
                      value={field.value || '#6366f1'}
                      onChange={field.onChange}
                      className="h-9 w-12 cursor-pointer rounded-lg border border-gray-200 bg-transparent dark:border-gray-700"
                    />
                  )}
                />
              </div>
            </div>

            <Controller
              control={control}
              name="widget_enabled"
              render={({ field }) => (
                <Toggle
                  checked={field.value}
                  onChange={field.onChange}
                  label="Enable chat widget"
                  description="Show the chat widget on your website."
                />
              )}
            />
            <Controller
              control={control}
              name="show_branding"
              render={({ field }) => (
                <Toggle
                  checked={field.value}
                  onChange={field.onChange}
                  label="Show “Powered by” branding"
                  description="Display SupportAI branding in the widget."
                />
              )}
            />
          </CardBody>
        </Card>

        {/* Widget messaging */}
        <Card className="lg:col-span-2">
          <CardHeader
            title="Widget Settings"
            subtitle="The first thing customers see when they open the chat."
          />
          <CardBody>
            <Textarea
              label="Welcome message"
              rows={3}
              {...register('welcome_message')}
            />

            {/* Live preview */}
            <div className="mt-5">
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-gray-400">
                Preview
              </p>
              <div className="max-w-sm rounded-2xl border border-gray-200 bg-white p-4 shadow-card dark:border-gray-800 dark:bg-gray-900">
                <div className="flex items-center gap-2">
                  <span
                    className="flex h-8 w-8 items-center justify-center rounded-lg text-white"
                    style={{ background: themeColor }}
                  >
                    {(watch('company_name') || 'A')[0]}
                  </span>
                  <span className="text-sm font-semibold text-gray-800 dark:text-gray-100">
                    {watch('company_name') || 'Your Company'}
                  </span>
                </div>
                <div className="mt-3 rounded-xl rounded-tl-sm bg-gray-100 px-3 py-2 text-sm text-gray-700 dark:bg-gray-800 dark:text-gray-200">
                  {watch('welcome_message') || 'Hi there! How can we help?'}
                </div>
              </div>
            </div>
          </CardBody>
        </Card>
      </div>

      <div className="mt-6 flex justify-end">
        <Button type="submit" loading={saving}>
          Save Settings
        </Button>
      </div>
    </form>
  )
}

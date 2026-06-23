import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import settingsService from '../../services/settingsService'
import { normalizeError } from '../../services/axiosInstance'

export const fetchSettings = createAsyncThunk(
  'settings/fetch',
  async (_, { rejectWithValue }) => {
    try {
      return await settingsService.get()
    } catch (err) {
      return rejectWithValue(normalizeError(err).message)
    }
  },
)

export const saveSettings = createAsyncThunk(
  'settings/save',
  async (payload, { rejectWithValue }) => {
    try {
      return await settingsService.update(payload)
    } catch (err) {
      return rejectWithValue(normalizeError(err).message)
    }
  },
)

const settingsSlice = createSlice({
  name: 'settings',
  initialState: { data: null, status: 'idle', saving: false, error: null },
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchSettings.pending, (state) => {
        state.status = 'loading'
      })
      .addCase(fetchSettings.fulfilled, (state, { payload }) => {
        state.status = 'succeeded'
        state.data = payload
      })
      .addCase(fetchSettings.rejected, (state, { payload }) => {
        state.status = 'failed'
        state.error = payload
      })
      .addCase(saveSettings.pending, (state) => {
        state.saving = true
      })
      .addCase(saveSettings.fulfilled, (state, { payload }) => {
        state.saving = false
        state.data = payload
      })
      .addCase(saveSettings.rejected, (state, { payload }) => {
        state.saving = false
        state.error = payload
      })
  },
})

export default settingsSlice.reducer

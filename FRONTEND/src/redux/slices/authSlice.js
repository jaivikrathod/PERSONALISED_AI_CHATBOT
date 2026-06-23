import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import authService from '../../services/authService'
import { normalizeError } from '../../services/axiosInstance'
import { STORAGE_KEYS } from '../../utils/constants'
import { storage, tokenStore } from '../../utils/storage'

// ---- thunks ------------------------------------------------------------
export const login = createAsyncThunk(
  'auth/login',
  async (credentials, { rejectWithValue }) => {
    try {
      const data = await authService.login(credentials)
      tokenStore.setTokens({ access: data.access, refresh: data.refresh })
      if (data.user) storage.setJSON(STORAGE_KEYS.USER, data.user)
      return data
    } catch (err) {
      return rejectWithValue(normalizeError(err).message)
    }
  },
)

export const fetchCurrentUser = createAsyncThunk(
  'auth/me',
  async (_, { rejectWithValue }) => {
    try {
      const user = await authService.me()
      storage.setJSON(STORAGE_KEYS.USER, user)
      return user
    } catch (err) {
      return rejectWithValue(normalizeError(err).message)
    }
  },
)

export const logout = createAsyncThunk('auth/logout', async () => {
  await authService.logout()
  tokenStore.clear()
})

// ---- slice -------------------------------------------------------------
const initialState = {
  user: storage.getJSON(STORAGE_KEYS.USER),
  accessToken: tokenStore.getAccess(),
  refreshToken: tokenStore.getRefresh(),
  status: 'idle', // idle | loading | succeeded | failed
  error: null,
}

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    // Hard logout triggered by axios interceptor on unrecoverable 401
    forceLogout(state) {
      tokenStore.clear()
      state.user = null
      state.accessToken = null
      state.refreshToken = null
      state.status = 'idle'
    },
    clearAuthError(state) {
      state.error = null
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(login.pending, (state) => {
        state.status = 'loading'
        state.error = null
      })
      .addCase(login.fulfilled, (state, { payload }) => {
        state.status = 'succeeded'
        state.user = payload.user || state.user
        state.accessToken = payload.access
        state.refreshToken = payload.refresh
      })
      .addCase(login.rejected, (state, { payload }) => {
        state.status = 'failed'
        state.error = payload || 'Login failed'
      })
      .addCase(fetchCurrentUser.fulfilled, (state, { payload }) => {
        state.user = payload
      })
      .addCase(logout.fulfilled, (state) => {
        state.user = null
        state.accessToken = null
        state.refreshToken = null
        state.status = 'idle'
      })
  },
})

export const { forceLogout, clearAuthError } = authSlice.actions
export default authSlice.reducer

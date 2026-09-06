import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import authService from '../../services/authService'
import { clearSession, tokenStore, userStore } from '../../utils/storage'

/**
 * Session state.
 *
 * `POST /auth/login/` issues a bearer token; that token is the credential and
 * every API call carries it. The cached profile in localStorage is for first
 * paint only — `restoreSession` re-validates it against `/auth/me/` on boot, so
 * a revoked or expired token cannot leave the UI looking signed in.
 */

// ---- thunks ------------------------------------------------------------
export const login = createAsyncThunk(
  'auth/login',
  async (credentials, { rejectWithValue }) => {
    try {
      const { token, user } = await authService.login(credentials)
      tokenStore.set(token)
      userStore.set(user)
      return user
    } catch (err) {
      return rejectWithValue(err.message || 'Login failed.')
    }
  },
)

export const register = createAsyncThunk(
  'auth/register',
  async ({ company, admin }, { rejectWithValue }) => {
    try {
      // Registration signs the new Admin straight in.
      const { token, user } = await authService.register({ company, admin })
      tokenStore.set(token)
      userStore.set(user)
      return user
    } catch (err) {
      return rejectWithValue(err.message || 'Registration failed.')
    }
  },
)

/** Boot-time check that the stored token is still good. */
export const restoreSession = createAsyncThunk(
  'auth/restore',
  async (_, { rejectWithValue }) => {
    if (!tokenStore.get()) return null
    try {
      const user = await authService.me()
      userStore.set(user)
      return user
    } catch {
      clearSession()
      return rejectWithValue(null)
    }
  },
)

export const logoutUser = createAsyncThunk('auth/logoutUser', async () => {
  try {
    await authService.logout()
  } catch {
    // A token that is already gone server-side is still a successful logout.
  }
  clearSession()
})

// ---- slice -------------------------------------------------------------
const authSlice = createSlice({
  name: 'auth',
  initialState: {
    // Optimistic: only trust a cached profile that still has a token beside it.
    user: tokenStore.get() ? userStore.get() : null,
    status: 'idle', // idle | loading | succeeded | failed
    error: null,
  },
  reducers: {
    logout(state) {
      clearSession()
      state.user = null
      state.status = 'idle'
      state.error = null
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
        state.user = payload
      })
      .addCase(login.rejected, (state, { payload }) => {
        state.status = 'failed'
        state.error = payload
      })
      .addCase(register.pending, (state) => {
        state.status = 'loading'
        state.error = null
      })
      .addCase(register.fulfilled, (state, { payload }) => {
        state.status = 'succeeded'
        state.user = payload
      })
      .addCase(register.rejected, (state, { payload }) => {
        state.status = 'failed'
        state.error = payload
      })
      .addCase(restoreSession.fulfilled, (state, { payload }) => {
        if (payload) state.user = payload
      })
      .addCase(restoreSession.rejected, (state) => {
        state.user = null
      })
      .addCase(logoutUser.fulfilled, (state) => {
        state.user = null
        state.status = 'idle'
        state.error = null
      })
  },
})

export const { logout, clearAuthError } = authSlice.actions
export default authSlice.reducer

import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import authService from '../../services/authService'
import { userStore } from '../../utils/storage'

/**
 * Session state. The backend issues no JWT — `POST /auth/login/` returns the
 * user profile, which we mirror into localStorage so a refresh keeps the
 * session. `isAuthenticated` is therefore simply "do we have a user".
 */

// ---- thunks ------------------------------------------------------------
export const login = createAsyncThunk(
  'auth/login',
  async (credentials, { rejectWithValue }) => {
    try {
      const user = await authService.login(credentials)
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
      return await authService.register({ company, admin })
    } catch (err) {
      return rejectWithValue(err.message || 'Registration failed.')
    }
  },
)

// ---- slice -------------------------------------------------------------
const authSlice = createSlice({
  name: 'auth',
  initialState: {
    user: userStore.get(),
    status: 'idle', // idle | loading | succeeded | failed
    error: null,
  },
  reducers: {
    logout(state) {
      userStore.clear()
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
      .addCase(register.fulfilled, (state) => {
        state.status = 'succeeded'
      })
      .addCase(register.rejected, (state, { payload }) => {
        state.status = 'failed'
        state.error = payload
      })
  },
})

export const { logout, clearAuthError } = authSlice.actions
export default authSlice.reducer

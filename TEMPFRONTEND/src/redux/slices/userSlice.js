import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import userService from '../../services/userService'

/**
 * Company user management (`users.ManagedUserViewSet`). Every request carries
 * the caller's `user_type` — the backend permission checks that query param.
 */

export const fetchUsers = createAsyncThunk(
  'users/fetch',
  async (_, { rejectWithValue }) => {
    try {
      return await userService.list()
    } catch (err) {
      return rejectWithValue(err.message || 'Failed to load users.')
    }
  },
)

export const createUser = createAsyncThunk(
  'users/create',
  async ({ payload }, { rejectWithValue }) => {
    try {
      return await userService.create(payload)
    } catch (err) {
      return rejectWithValue(err.message || 'Failed to save user.')
    }
  },
)

export const updateUser = createAsyncThunk(
  'users/update',
  async ({ id, payload }, { rejectWithValue }) => {
    try {
      return await userService.update(id, payload)
    } catch (err) {
      return rejectWithValue(err.message || 'Failed to save user.')
    }
  },
)

export const deleteUser = createAsyncThunk(
  'users/delete',
  async ({ id }, { rejectWithValue }) => {
    try {
      return await userService.remove(id)
    } catch (err) {
      return rejectWithValue(err.message || 'Failed to delete user.')
    }
  },
)

const userSlice = createSlice({
  name: 'users',
  initialState: {
    items: [],
    status: 'idle', // idle | loading | succeeded | failed
    saving: false,
    deletingId: null,
    error: null,
  },
  reducers: {
    clearUserError(state) {
      state.error = null
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchUsers.pending, (state) => {
        state.status = 'loading'
        state.error = null
      })
      .addCase(fetchUsers.fulfilled, (state, { payload }) => {
        state.status = 'succeeded'
        state.items = Array.isArray(payload) ? payload : payload?.results || []
      })
      .addCase(fetchUsers.rejected, (state, { payload }) => {
        state.status = 'failed'
        state.error = payload
      })
      .addCase(createUser.pending, (state) => {
        state.saving = true
        state.error = null
      })
      .addCase(createUser.fulfilled, (state, { payload }) => {
        state.saving = false
        state.items.unshift(payload)
      })
      .addCase(createUser.rejected, (state, { payload }) => {
        state.saving = false
        state.error = payload
      })
      .addCase(updateUser.pending, (state) => {
        state.saving = true
        state.error = null
      })
      .addCase(updateUser.fulfilled, (state, { payload }) => {
        state.saving = false
        const index = state.items.findIndex((item) => item.id === payload.id)
        if (index !== -1) state.items[index] = payload
      })
      .addCase(updateUser.rejected, (state, { payload }) => {
        state.saving = false
        state.error = payload
      })
      .addCase(deleteUser.pending, (state, { meta }) => {
        state.deletingId = meta.arg.id
        state.error = null
      })
      .addCase(deleteUser.fulfilled, (state, { payload: id }) => {
        state.deletingId = null
        state.items = state.items.filter((item) => item.id !== id)
      })
      .addCase(deleteUser.rejected, (state, { payload }) => {
        state.deletingId = null
        state.error = payload
      })
  },
})

export const { clearUserError } = userSlice.actions
export default userSlice.reducer

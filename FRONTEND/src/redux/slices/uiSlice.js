import { createSlice } from '@reduxjs/toolkit'

/**
 * Cross-cutting UI state: mobile sidebar drawer + transient toasts.
 * Theme itself lives in useTheme (DOM + localStorage) to avoid re-rendering
 * the whole tree on toggle.
 */
let toastId = 0

const uiSlice = createSlice({
  name: 'ui',
  initialState: {
    sidebarOpen: false, // mobile drawer
    toasts: [],
  },
  reducers: {
    toggleSidebar(state) {
      state.sidebarOpen = !state.sidebarOpen
    },
    setSidebar(state, { payload }) {
      state.sidebarOpen = payload
    },
    addToast: {
      reducer(state, { payload }) {
        state.toasts.push(payload)
      },
      prepare({ type = 'info', message }) {
        return { payload: { id: ++toastId, type, message } }
      },
    },
    removeToast(state, { payload }) {
      state.toasts = state.toasts.filter((t) => t.id !== payload)
    },
  },
})

export const { toggleSidebar, setSidebar, addToast, removeToast } =
  uiSlice.actions
export default uiSlice.reducer

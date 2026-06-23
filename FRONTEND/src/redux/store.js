import { configureStore } from '@reduxjs/toolkit'
import { setAuthFailureHandler } from '../services/axiosInstance'
import authReducer, { forceLogout } from './slices/authSlice'
import uiReducer from './slices/uiSlice'
import knowledgeBaseReducer from './slices/knowledgeBaseSlice'
import chatbotReducer from './slices/chatbotSlice'
import conversationReducer from './slices/conversationSlice'
import chatReducer from './slices/chatSlice'
import analyticsReducer from './slices/analyticsSlice'
import agentReducer from './slices/agentSlice'
import settingsReducer from './slices/settingsSlice'

export const store = configureStore({
  reducer: {
    auth: authReducer,
    ui: uiReducer,
    kb: knowledgeBaseReducer,
    chatbots: chatbotReducer,
    conversations: conversationReducer,
    chat: chatReducer,
    analytics: analyticsReducer,
    agents: agentReducer,
    settings: settingsReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        // FormData / File payloads (logo + bulk upload) aren't serializable
        ignoredActionPaths: ['meta.arg', 'payload.logo'],
      },
    }),
})

// When axios exhausts token refresh, hard-logout through redux.
setAuthFailureHandler(() => {
  store.dispatch(forceLogout())
})

export default store

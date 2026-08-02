import { configureStore } from '@reduxjs/toolkit'
import authReducer from './slices/authSlice'
import uiReducer from './slices/uiSlice'
import questionReducer from './slices/questionSlice'
import unansweredReducer from './slices/unansweredSlice'
import userReducer from './slices/userSlice'
import customerChatReducer from './slices/customerChatSlice'
import agentChatReducer from './slices/agentChatSlice'

export const store = configureStore({
  reducer: {
    auth: authReducer,
    ui: uiReducer,
    questions: questionReducer,
    unanswered: unansweredReducer,
    users: userReducer,
    customerChat: customerChatReducer,
    agentChat: agentChatReducer,
  },
})

export default store

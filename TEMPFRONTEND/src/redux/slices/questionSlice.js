import { createAsyncThunk, createSelector, createSlice } from '@reduxjs/toolkit'
import questionService from '../../services/questionService'
import vectorService from '../../services/vectorService'

/**
 * The company knowledge base: question/answer pairs and their vectorization
 * state. Mirrors `questions.QuestionViewSet` + `POST /vectorize/:companyId/`.
 */

export const fetchQuestions = createAsyncThunk(
  'questions/fetch',
  async ({ companyId, search } = {}, { rejectWithValue }) => {
    try {
      return await questionService.list(companyId, { search })
    } catch (err) {
      return rejectWithValue(err.message || 'Failed to load questions.')
    }
  },
)

export const createQuestion = createAsyncThunk(
  'questions/create',
  async ({ companyId, question, answer }, { rejectWithValue }) => {
    try {
      return await questionService.create({ companyId, question, answer })
    } catch (err) {
      return rejectWithValue(err.message || 'Failed to add question.')
    }
  },
)

export const deleteQuestion = createAsyncThunk(
  'questions/delete',
  async (id, { rejectWithValue }) => {
    try {
      return await questionService.remove(id)
    } catch (err) {
      return rejectWithValue(err.message || 'Failed to delete question.')
    }
  },
)

/**
 * Convert every un-vectorized question of the company into embeddings.
 * Resolves to the backend summary:
 *   { message, total_questions?, processed_questions?, failed_questions? }
 */
export const vectorizeQuestions = createAsyncThunk(
  'questions/vectorize',
  async (companyId, { rejectWithValue }) => {
    try {
      return await vectorService.vectorizeCompany(companyId)
    } catch (err) {
      return rejectWithValue(err.message || 'Vectorization failed.')
    }
  },
)

const questionSlice = createSlice({
  name: 'questions',
  initialState: {
    items: [],
    search: '',
    status: 'idle', // idle | loading | succeeded | failed
    mutating: false,
    vectorizing: false,
    error: null,
  },
  reducers: {
    setQuestionSearch(state, { payload }) {
      state.search = payload
    },
    clearQuestionError(state) {
      state.error = null
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchQuestions.pending, (state) => {
        state.status = 'loading'
        state.error = null
      })
      .addCase(fetchQuestions.fulfilled, (state, { payload }) => {
        state.status = 'succeeded'
        state.items = Array.isArray(payload) ? payload : payload?.results || []
      })
      .addCase(fetchQuestions.rejected, (state, { payload }) => {
        state.status = 'failed'
        state.error = payload
      })
      .addCase(createQuestion.pending, (state) => {
        state.mutating = true
        state.error = null
      })
      .addCase(createQuestion.fulfilled, (state, { payload }) => {
        state.mutating = false
        state.items.unshift(payload)
      })
      .addCase(createQuestion.rejected, (state, { payload }) => {
        state.mutating = false
        state.error = payload
      })
      .addCase(deleteQuestion.fulfilled, (state, { payload: id }) => {
        state.items = state.items.filter((item) => item.id !== id)
      })
      .addCase(deleteQuestion.rejected, (state, { payload }) => {
        state.error = payload
      })
      .addCase(vectorizeQuestions.pending, (state) => {
        state.vectorizing = true
        state.error = null
      })
      .addCase(vectorizeQuestions.fulfilled, (state) => {
        state.vectorizing = false
      })
      .addCase(vectorizeQuestions.rejected, (state, { payload }) => {
        state.vectorizing = false
        state.error = payload
      })
  },
})

// ---- selectors ---------------------------------------------------------
// Memoized so the derived object keeps its identity between unrelated store
// updates and doesn't re-render the page on every action.
export const selectQuestionStats = createSelector(
  (state) => state.questions.items,
  (items) => {
    const vectorized = items.filter((item) => item.is_vectorized).length
    return { total: items.length, vectorized, pending: items.length - vectorized }
  },
)

export const { setQuestionSearch, clearQuestionError } = questionSlice.actions
export default questionSlice.reducer

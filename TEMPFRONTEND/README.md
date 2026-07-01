# SupportAI — AI Customer Support SaaS (Frontend)

React 18-style SPA (running on React 19 + Vite) for an AI customer-support
platform. Talks to a Django REST API over JWT, with realtime conversations &
agent chat over Socket.io.

## Tech stack

- **React** + **Vite** (JSX, functional components, hooks only)
- **React Router v6** — routing & route guards
- **Redux Toolkit** + **react-redux** — state with `createAsyncThunk`
- **Axios** — API client with JWT + refresh-token interceptors
- **React Hook Form** — all forms & validation
- **Tailwind CSS** (v3) — styling, `darkMode: 'class'`, fully responsive
- **Heroicons** — icons
- **Socket.io-client** — realtime messaging / presence / typing
- **Recharts** — analytics charts

## Getting started

```bash
npm install
cp .env.example .env     # set your API + WS URLs
npm run dev              # http://localhost:5173
npm run build            # production build
```

### Environment variables (`.env`)

| Var | Purpose |
| --- | --- |
| `VITE_API_BASE_URL` | Django REST API base, e.g. `http://localhost:8000/api` |
| `VITE_WS_URL` | Socket.io endpoint, e.g. `http://localhost:8000` |
| `VITE_WIDGET_DOMAIN` | Domain used in the generated widget snippet |

> **Demo mode:** every page falls back to realistic mock data
> (`src/utils/mockData.js`) when the API returns nothing, so the whole UI is
> presentable before the backend is wired up. Remove those fallbacks once your
> endpoints are live.

## Folder structure

```
src/
  components/
    ui/            # Reusable design-system kit (Button, Modal, Table, …)
    layout/        # DashboardLayout, Sidebar, Topbar, Breadcrumbs, dropdowns
    charts/        # ChartCard + shared Recharts theme
    chat/          # MessageThread, MessageBubble, Composer, TypingIndicator
  pages/
    auth/          # LoginPage
    dashboard/     # DashboardPage
    knowledge-base/# List + FAQ form + bulk upload
    chatbots/      # List + form + widget-script modals
    conversations/ # Intercom-style inbox
    agents/        # Live agent dashboard (take over / assign / transfer / resolve)
    analytics/     # Charts + date range
    unanswered/    # Unanswered questions -> convert to FAQ
    settings/      # Company / branding / widget settings
  redux/
    store.js
    slices/        # auth, ui, kb, chatbot, conversation, chat, analytics, agent, settings
  services/        # axiosInstance + one service per domain + socketService
  hooks/           # useAuth, useTheme, useDebounce, useConversationSocket
  routes/          # AppRoutes, ProtectedRoute, PublicRoute, navigation config
  utils/           # constants, format, storage, cn, mockData
```

## Auth flow

- `POST /auth/login/` → `{ access, refresh, user }`.
- Tokens persist in Redux **and** localStorage (`tokenStore`).
- `axiosInstance` attaches `Authorization: Bearer <access>` and transparently
  refreshes via `POST /auth/token/refresh/` on a 401 (concurrent requests are
  queued). An unrecoverable refresh triggers a hard logout.
- `ProtectedRoute` redirects unauthenticated users to `/login` (preserving the
  attempted path); `PublicRoute` keeps logged-in users out of `/login`.

## Expected API endpoints

Each service file documents the exact endpoints it calls — adjust paths to match
your Django URLs. Summary:

| Domain | Endpoints |
| --- | --- |
| Auth | `/auth/login/`, `/auth/token/refresh/`, `/auth/me/`, `/auth/logout/` |
| Knowledge Base | `GET/POST /knowledge-base/`, `PUT/DELETE /knowledge-base/:id/`, `POST /knowledge-base/bulk-upload/` |
| Chatbots | `GET/POST /chatbots/`, `PUT/DELETE /chatbots/:id/` |
| Conversations | `GET /conversations/`, `GET /conversations/:id/messages/`, `POST .../messages/`, `PATCH /conversations/:id/` |
| Agents | `GET /agents/`, `POST /conversations/:id/{take-over,assign,transfer,resolve}/` |
| Analytics | `/analytics/overview/`, `/analytics/conversations-series/`, `/analytics/top-faqs/`, `/analytics/unanswered/`, `POST /analytics/unanswered/:id/convert/` |
| Settings | `GET /settings/`, `PATCH /settings/` |

Paginated list endpoints may return either a plain array or DRF-style
`{ results, count }` — both are handled.

## Realtime (Socket.io)

`socketService` connects with the JWT in the handshake `auth`. Server events
consumed: `message:new`, `conversation:new`, `typing`, `presence`. Client emits:
`conversation:join/leave`, `typing`, `message:send`. Rename to match your
Channels/Socket layer in `src/services/socketService.js`.

## Dark mode

Toggled from the topbar; `useTheme` sets the `dark` class on `<html>` and
persists the choice. Every component has dark variants.

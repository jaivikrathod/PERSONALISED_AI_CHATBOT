/**
 * Demo data used as a graceful fallback when the API isn't reachable yet,
 * so the UI is fully presentable during frontend development.
 * Remove these fallbacks once every endpoint is live.
 */
export const mockOverview = {
  total_conversations: 8421,
  resolved_by_ai: 6120,
  resolved_by_agent: 1583,
  escalated: 412,
  active_agents: 14,
  unanswered: 38,
  total_conversations_delta: 12,
  resolved_by_ai_delta: 8,
  resolved_by_agent_delta: -3,
  escalated_delta: 5,
}

export const mockDailySeries = [
  { label: 'Mon', conversations: 320, resolved: 240 },
  { label: 'Tue', conversations: 410, resolved: 300 },
  { label: 'Wed', conversations: 380, resolved: 290 },
  { label: 'Thu', conversations: 520, resolved: 410 },
  { label: 'Fri', conversations: 610, resolved: 480 },
  { label: 'Sat', conversations: 290, resolved: 230 },
  { label: 'Sun', conversations: 240, resolved: 200 },
]

export const mockWeeklySeries = [
  { label: 'W1', conversations: 1820 },
  { label: 'W2', conversations: 2110 },
  { label: 'W3', conversations: 1980 },
  { label: 'W4', conversations: 2510 },
]

export const mockTopFaqs = [
  { question: 'How do I reset my password?', count: 482 },
  { question: 'Where can I track my order?', count: 391 },
  { question: 'What is your refund policy?', count: 322 },
  { question: 'How do I upgrade my plan?', count: 268 },
  { question: 'Do you offer team discounts?', count: 154 },
]

export const mockChatbots = [
  { id: 1, name: 'Website Bot', widget_token: 'wgt_8fa2c1b9e4', status: 'active', created_at: '2026-04-12' },
  { id: 2, name: 'Support Center Bot', widget_token: 'wgt_2c7d54a0f1', status: 'active', created_at: '2026-05-02' },
  { id: 3, name: 'Sales Assistant', widget_token: 'wgt_a91b0c33de', status: 'inactive', created_at: '2026-05-21' },
]

export const mockFaqs = Array.from({ length: 12 }, (_, i) => ({
  id: i + 1,
  question: [
    'How do I reset my password?',
    'Where can I track my order?',
    'What is your refund policy?',
    'How do I upgrade my plan?',
    'Do you offer team discounts?',
    'How do I cancel my subscription?',
    'Is there a free trial?',
    'How do I contact support?',
    'Can I export my data?',
    'Do you support SSO?',
    'How do I add team members?',
    'What payment methods do you accept?',
  ][i],
  answer: 'This is a sample answer maintained in your knowledge base and used by the AI to resolve conversations automatically.',
  created_at: `2026-0${(i % 6) + 1}-1${i % 9}`,
}))

export const mockConversations = Array.from({ length: 8 }, (_, i) => ({
  id: i + 1,
  customer_name: ['Alice Johnson', 'Marcus Lee', 'Priya Nair', 'Tom Becker', 'Sara Kim', 'David Cohen', 'Lena Park', 'Omar Said'][i],
  last_message: ['Thanks, that worked!', 'I still can’t log in', 'When will it ship?', 'Can I get a refund?', 'Great, appreciate it', 'Is anyone there?', 'How do I upgrade?', 'My order is late'][i],
  status: ['resolved', 'open', 'pending', 'escalated', 'resolved', 'open', 'open', 'escalated'][i],
  unread_count: [0, 2, 0, 1, 0, 3, 0, 1][i],
  channel: 'widget',
  updated_at: new Date(Date.now() - i * 3600_000).toISOString(),
}))

export const mockMessages = [
  { id: 1, body: 'Hi, I can’t log into my account.', sender: 'customer', author: 'Customer', created_at: new Date(Date.now() - 9 * 60000).toISOString() },
  { id: 2, body: 'I’m sorry to hear that! Have you tried resetting your password from the login page?', sender: 'ai', author: 'AI Assistant', created_at: new Date(Date.now() - 8 * 60000).toISOString() },
  { id: 3, body: 'Yes but I never get the email.', sender: 'customer', author: 'Customer', created_at: new Date(Date.now() - 6 * 60000).toISOString() },
  { id: 4, body: 'Let me connect you with an agent who can help.', sender: 'ai', author: 'AI Assistant', created_at: new Date(Date.now() - 5 * 60000).toISOString() },
  { id: 5, body: 'Hi, this is Jordan from support — checking your account now.', sender: 'agent', author: 'Jordan (Agent)', created_at: new Date(Date.now() - 3 * 60000).toISOString() },
]

export const mockAgents = [
  { id: 1, name: 'Jordan Miles', email: 'jordan@company.com', status: 'online', active_chats: 3, role: 'Senior Agent' },
  { id: 2, name: 'Aisha Khan', email: 'aisha@company.com', status: 'online', active_chats: 1, role: 'Agent' },
  { id: 3, name: 'Diego Torres', email: 'diego@company.com', status: 'away', active_chats: 0, role: 'Agent' },
  { id: 4, name: 'Mei Chen', email: 'mei@company.com', status: 'offline', active_chats: 0, role: 'Agent' },
]

export const mockUnanswered = Array.from({ length: 6 }, (_, i) => ({
  id: i + 1,
  question: [
    'Do you integrate with Salesforce?',
    'Can I schedule a demo?',
    'What languages are supported?',
    'Is there an on-premise option?',
    'How do I migrate from Zendesk?',
    'Do you have a mobile app?',
  ][i],
  count: [42, 31, 27, 19, 15, 9][i],
  last_asked: new Date(Date.now() - i * 86400000).toISOString(),
}))

export const mockSettings = {
  company_name: 'Acme Inc.',
  support_email: 'support@acme.com',
  theme_color: '#6366f1',
  logo: null,
  welcome_message: 'Hi there! 👋 How can we help you today?',
  widget_enabled: true,
  show_branding: true,
}

from django.urls import path

from .views import (
    AgentChatHistoryView,
    AgentChatListView,
    AgentCloseChatView,
    AgentSendMessageView,
    AssignAgentView,
    ChatHistoryView,
    ChatWidgetConfigView,
)

urlpatterns = [
    # Public widget (anonymous visitors). `history` is guarded by the session's
    # own public_token rather than by a bearer token.
    path("chat/widget/", ChatWidgetConfigView.as_view(), name="chat-widget-config"),
    path("chat/history/", ChatHistoryView.as_view(), name="chat-history"),
    path("chat/sessions/assign/", AssignAgentView.as_view(), name="chat-assign-agent"),
    # Agent-facing routes. The agent is taken from the token, never the request.
    path("agent/chats/", AgentChatListView.as_view(), name="agent-chats"),
    path("agent/chats/history/", AgentChatHistoryView.as_view(), name="agent-chat-history"),
    path("agent/chats/send/", AgentSendMessageView.as_view(), name="agent-chat-send"),
    path("agent/chats/close/", AgentCloseChatView.as_view(), name="agent-chat-close"),
]

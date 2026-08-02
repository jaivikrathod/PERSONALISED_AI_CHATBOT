from django.urls import path

from .views import (
    AgentChatHistoryView,
    AgentChatListView,
    AgentCloseChatView,
    AgentSendMessageView,
    AssignAgentView,
    ChatHistoryView,
    ChatSessionListView,
)

urlpatterns = [
    path("chat/sessions/", ChatSessionListView.as_view(), name="chat-sessions"),
    path("chat/history/", ChatHistoryView.as_view(), name="chat-history"),
    path("chat/sessions/assign/", AssignAgentView.as_view(), name="chat-assign-agent"),
    # Agent-facing routes.
    path("agent/chats/", AgentChatListView.as_view(), name="agent-chats"),
    path("agent/chats/history/", AgentChatHistoryView.as_view(), name="agent-chat-history"),
    path("agent/chats/send/", AgentSendMessageView.as_view(), name="agent-chat-send"),
    path("agent/chats/close/", AgentCloseChatView.as_view(), name="agent-chat-close"),
]

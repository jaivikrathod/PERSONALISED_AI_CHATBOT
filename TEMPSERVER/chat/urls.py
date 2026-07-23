from django.urls import path

from .views import ChatHistoryView, ChatSessionListView

urlpatterns = [
    path("chat/sessions/", ChatSessionListView.as_view(), name="chat-sessions"),
    path("chat/history/", ChatHistoryView.as_view(), name="chat-history"),
]

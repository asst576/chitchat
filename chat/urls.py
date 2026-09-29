from django.urls import path

from chat import views

urlpatterns = [
    path("providers/", views.providers, name="api-providers"),
    path("conversations/", views.conversation_list, name="api-conversations"),
    path("conversations/<uuid:conversation_id>/", views.conversation_detail, name="api-conversation-detail"),
    path("messages/", views.new_message, name="api-new-message"),
    path(
        "conversations/<uuid:conversation_id>/messages/",
        views.conversation_message,
        name="api-conversation-message",
    ),
    path(
        "conversations/<uuid:conversation_id>/retry/",
        views.retry_message,
        name="api-retry-message",
    ),
]

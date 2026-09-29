import uuid

from django.db import models
from django.db.models import Q


class Provider(models.TextChoices):
    OPENAI = "openai", "OpenAI API"
    ANTHROPIC = "anthropic", "Anthropic API"
    GOOGLE = "google", "Google Gemini API"


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=120, default="New chat")
    provider = models.CharField(max_length=20, choices=Provider.choices)
    model_id = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at", "-id")
        indexes = [models.Index(fields=("-updated_at", "-id"), name="chat_recent_idx")]
        constraints = [
            models.CheckConstraint(
                condition=Q(provider__in=Provider.values),
                name="chat_convo_provider_ck",
            ),
        ]

    def __str__(self):
        return self.title


class Message(models.Model):
    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=12, choices=Role.choices)
    content = models.TextField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.COMPLETED)
    provider = models.CharField(max_length=20, choices=Provider.choices, blank=True)
    model_id = models.CharField(max_length=120, blank=True)
    failure_code = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at", "id")
        indexes = [models.Index(fields=("conversation", "created_at", "id"), name="chat_msg_order_idx")]
        constraints = [
            models.CheckConstraint(
                condition=Q(role__in=("user", "assistant")),
                name="chat_msg_role_ck",
            ),
            models.CheckConstraint(
                condition=Q(status__in=("pending", "completed", "failed")),
                name="chat_msg_status_ck",
            ),
            models.CheckConstraint(
                condition=Q(provider__in=Provider.values) | Q(provider=""),
                name="chat_msg_provider_ck",
            ),
        ]

    def __str__(self):
        return f"{self.role} message in {self.conversation_id}"

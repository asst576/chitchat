import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q


class Provider(models.TextChoices):
    OPENAI = "openai", "OpenAI API"
    ANTHROPIC = "anthropic", "Anthropic API"
    GOOGLE = "google", "Google Gemini API"


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="conversations",
    )
    title = models.CharField(max_length=120, default="New chat")
    provider = models.CharField(max_length=20, choices=Provider.choices)
    model_id = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at", "-id")
        indexes = [
            models.Index(fields=("-updated_at", "-id"), name="chat_recent_idx"),
            models.Index(fields=("owner", "-updated_at"), name="chat_owner_recent_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(provider__in=Provider.values),
                name="chat_convo_provider_ck",
            ),
        ]

    def __str__(self):
        return self.title


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    display_name = models.CharField(max_length=120, blank=True)
    system_prompt = models.TextField(blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.display_name or self.user.get_username()


class BillingAccount(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="billing_account",
    )
    account_name = models.CharField(max_length=120, default="Personal")
    currency_code = models.CharField(max_length=3, default="USD", editable=False)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    available_credit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("2.00"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(available_credit__gte=0),
                name="chat_billing_credit_nonneg_ck",
            ),
        ]

    def __str__(self):
        return "{} billing account".format(self.user.get_username())


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

from django.db import DatabaseError, transaction
from django.db.models import Q
from django.utils import timezone

from chat.models import Conversation, Message
from chat.providers import get_model_option
from chat.services.proxy_client import ProxyClient, ProxyFailure

MAX_PROMPT_LENGTH = 20_000
TITLE_LENGTH = 120


class ChatError(Exception):
    def __init__(self, code, message, http_status):
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.conversation_id = None
        self.assistant_message_id = None


def submit_prompt(user, prompt, provider_id, model_id, conversation_id=None):
    prompt = prompt.strip() if isinstance(prompt, str) else ""
    if not prompt:
        raise ChatError("empty_prompt", "Enter a message before sending.", 400)
    if len(prompt) > MAX_PROMPT_LENGTH:
        raise ChatError("prompt_too_long", "Messages must be 20,000 characters or fewer.", 400)
    if get_model_option(provider_id, model_id) is None:
        raise ChatError("unsupported_model", "That provider/model combination is not enabled.", 400)

    with transaction.atomic():
        if conversation_id is None:
            title = prompt[:TITLE_LENGTH].rstrip()
            if len(prompt) > TITLE_LENGTH:
                title = f"{prompt[: TITLE_LENGTH - 3].rstrip()}..."
            conversation = Conversation.objects.create(
                owner=user,
                title=title or "New chat",
                provider=provider_id,
                model_id=model_id,
            )
        else:
            try:
                conversation = Conversation.objects.get(pk=conversation_id, owner=user)
            except (Conversation.DoesNotExist, ValueError):
                raise ChatError("conversation_not_found", "Conversation not found.", 404) from None

        if conversation.messages.filter(status=Message.Status.PENDING).exists():
            raise ChatError(
                "request_in_progress",
                "A response is already in progress for this conversation.",
                409,
            )

        conversation.provider = provider_id
        conversation.model_id = model_id
        conversation.updated_at = timezone.now()
        conversation.save(update_fields=("provider", "model_id", "updated_at"))
        Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content=prompt,
        )
        assistant_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="",
            status=Message.Status.PENDING,
            provider=provider_id,
            model_id=model_id,
        )
        context = _build_context(conversation, assistant_message.pk)
        system_prompt = getattr(getattr(user, "profile", None), "system_prompt", "")

    return _finish_assistant(conversation, assistant_message, context, system_prompt)


def retry_failed_response(user, conversation_id, assistant_message_id):
    with transaction.atomic():
        try:
            conversation = Conversation.objects.get(pk=conversation_id, owner=user)
            assistant_message = conversation.messages.get(
                pk=assistant_message_id,
                role=Message.Role.ASSISTANT,
                status=Message.Status.FAILED,
            )
        except (Conversation.DoesNotExist, Message.DoesNotExist, ValueError):
            raise ChatError("retry_not_available", "That response cannot be retried.", 404) from None

        latest = conversation.messages.order_by("-created_at", "-id").first()
        if latest is None or latest.pk != assistant_message.pk:
            raise ChatError(
                "retry_not_available",
                "Only the latest failed response can be retried.",
                409,
            )
        if conversation.messages.filter(status=Message.Status.PENDING).exists():
            raise ChatError(
                "request_in_progress",
                "A response is already in progress for this conversation.",
                409,
            )

        previous = (
            conversation.messages.filter(
                Q(created_at__lt=assistant_message.created_at)
                | Q(created_at=assistant_message.created_at, id__lt=assistant_message.id)
            )
            .order_by("-created_at", "-id")
            .first()
        )
        if previous is None or previous.role != Message.Role.USER:
            raise ChatError("retry_not_available", "That response cannot be retried.", 409)

        assistant_message.status = Message.Status.PENDING
        assistant_message.failure_code = ""
        assistant_message.save(update_fields=("status", "failure_code"))
        context = _build_context(conversation, assistant_message.pk)
        system_prompt = getattr(getattr(user, "profile", None), "system_prompt", "")

    return _finish_assistant(conversation, assistant_message, context, system_prompt)


def _build_context(conversation, pending_assistant_id):
    messages = list(conversation.messages.order_by("created_at", "id"))
    context = []
    index = 0
    while index < len(messages):
        message = messages[index]
        if message.role != Message.Role.USER:
            index += 1
            continue

        following = messages[index + 1] if index + 1 < len(messages) else None
        if following is None or following.role != Message.Role.ASSISTANT:
            index += 1
            continue
        if following.pk == pending_assistant_id and following.status == Message.Status.PENDING:
            context.append({"role": message.role, "content": message.content})
        elif following.status == Message.Status.COMPLETED:
            context.extend(
                (
                    {"role": message.role, "content": message.content},
                    {"role": following.role, "content": following.content},
                )
            )
        index += 2
    return context


def _finish_assistant(conversation, assistant_message, context, system_prompt):
    try:
        answer = ProxyClient().generate(
            conversation.provider,
            assistant_message.model_id,
            context,
            system_prompt=system_prompt,
        )
    except ProxyFailure as error:
        Message.objects.filter(pk=assistant_message.pk).update(
            status=Message.Status.FAILED,
            failure_code=error.code,
        )
        error.conversation_id = str(conversation.pk)
        error.assistant_message_id = str(assistant_message.pk)
        raise

    try:
        with transaction.atomic():
            Message.objects.filter(pk=assistant_message.pk).update(
                content=answer,
                status=Message.Status.COMPLETED,
                failure_code="",
            )
            Conversation.objects.filter(pk=conversation.pk).update(updated_at=timezone.now())
    except DatabaseError:
        try:
            Message.objects.filter(pk=assistant_message.pk).update(
                status=Message.Status.FAILED,
                failure_code="persistence_failed",
            )
        except DatabaseError:
            pass
        error = ChatError(
            "persistence_failed",
            "The response could not be saved. Reload the conversation before retrying.",
            503,
        )
        error.conversation_id = str(conversation.pk)
        error.assistant_message_id = str(assistant_message.pk)
        raise error from None
    assistant_message.content = answer
    assistant_message.status = Message.Status.COMPLETED
    assistant_message.failure_code = ""
    return conversation, assistant_message

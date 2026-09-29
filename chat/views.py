import json

from django.core.exceptions import RequestDataTooBig
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from chat.models import Conversation, Message
from chat.providers import list_model_options
from chat.services.conversations import ChatError, retry_failed_response, submit_prompt
from chat.services.proxy_client import ProxyFailure

PROXY_BEHAVIOR_NOTICE = (
    "The proxy exposes OpenAI, Anthropic, and Gemini-compatible APIs, but its documentation "
    "states that all three currently use DeepSeek Flash behind the interface."
)

FAILURE_MESSAGES = {
    "provider_not_configured": "The selected provider is not configured on the server.",
    "provider_authentication_failed": "The provider key was rejected. Check the server-side configuration.",
    "rate_limited": "The AI service is rate limited. Wait before trying again.",
    "proxy_timeout": "The AI service timed out.",
    "proxy_unavailable": "The AI service is temporarily unavailable.",
    "proxy_failure": "The AI service could not complete the request.",
    "proxy_rejected_request": "The AI service rejected the request.",
    "invalid_response": "The AI service returned an invalid response.",
    "empty_response": "The AI service returned an empty response.",
    "incomplete_response": "The AI response did not complete normally.",
    "content_filtered": "The AI service did not return a usable response.",
    "persistence_failed": "The response could not be saved. Reload the conversation before retrying.",
}


def _read_json(request):
    if request.content_type != "application/json":
        return None
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError, RequestDataTooBig):
        return None
    return data if isinstance(data, dict) else None


def _conversation_json(conversation):
    return {
        "id": str(conversation.pk),
        "title": conversation.title,
        "provider_id": conversation.provider,
        "model_id": conversation.model_id,
        "updated_at": conversation.updated_at.isoformat(),
    }


def _message_json(message):
    return {
        "id": message.pk,
        "role": message.role,
        "content": message.content,
        "status": message.status,
        "failure_code": message.failure_code,
        "failure_message": FAILURE_MESSAGES.get(message.failure_code, "The response failed.")
        if message.status == Message.Status.FAILED
        else "",
        "provider_id": message.provider,
        "model_id": message.model_id,
        "created_at": message.created_at.isoformat(),
    }


def _error_response(error):
    body = {
        "error": {"code": error.code, "message": error.message},
    }
    if error.conversation_id:
        body["conversation_id"] = error.conversation_id
    if error.assistant_message_id:
        body["assistant_message_id"] = error.assistant_message_id
    return JsonResponse(body, status=error.http_status)


@require_GET
def providers(request):
    return JsonResponse({"providers": list_model_options(), "notice": PROXY_BEHAVIOR_NOTICE})


@require_GET
def conversation_list(request):
    conversations = Conversation.objects.all()[:100]
    return JsonResponse({"conversations": [_conversation_json(item) for item in conversations]})


@require_GET
def conversation_detail(request, conversation_id):
    try:
        conversation = Conversation.objects.get(pk=conversation_id)
    except Conversation.DoesNotExist:
        return JsonResponse({"error": {"code": "not_found", "message": "Conversation not found."}}, status=404)
    messages = conversation.messages.order_by("created_at", "id")
    return JsonResponse(
        {
            "conversation": _conversation_json(conversation),
            "messages": [_message_json(item) for item in messages],
        }
    )


def _submit(request, conversation_id=None):
    data = _read_json(request)
    if data is None:
        return JsonResponse(
            {"error": {"code": "invalid_json", "message": "A JSON object is required."}},
            status=400,
        )
    try:
        conversation, assistant_message = submit_prompt(
            data.get("prompt"),
            data.get("provider_id"),
            data.get("model_id"),
            conversation_id=conversation_id,
        )
    except ChatError as error:
        return _error_response(error)
    except ProxyFailure as error:
        return _error_response(error)
    return JsonResponse(
        {
            "conversation": _conversation_json(conversation),
            "assistant_message": _message_json(assistant_message),
        }
    )


@require_POST
def new_message(request):
    return _submit(request)


@require_POST
def conversation_message(request, conversation_id):
    return _submit(request, conversation_id)


@require_POST
def retry_message(request, conversation_id):
    data = _read_json(request)
    if data is None or not isinstance(data.get("assistant_message_id"), int):
        return JsonResponse(
            {"error": {"code": "invalid_request", "message": "A response ID is required."}},
            status=400,
        )
    try:
        conversation, assistant_message = retry_failed_response(
            conversation_id,
            data["assistant_message_id"],
        )
    except ChatError as error:
        return _error_response(error)
    except ProxyFailure as error:
        return _error_response(error)
    return JsonResponse(
        {
            "conversation": _conversation_json(conversation),
            "assistant_message": _message_json(assistant_message),
        }
    )

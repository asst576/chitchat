import json
from functools import wraps

from django.conf import settings
from django.contrib.auth import get_user_model, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.exceptions import RequestDataTooBig
from django.db import transaction
from django.http import HttpResponse, HttpResponseNotFound, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from chat.forms import ProfileForm, SignupForm
from chat.models import BillingAccount, Conversation, Message, UserProfile
from chat.providers import list_model_options
from chat.services.accounts import provision_user_account
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


def api_login_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(
                {"error": {"code": "authentication_required", "message": "Sign in to continue."}},
                status=401,
            )
        return view(request, *args, **kwargs)

    return wrapped


class AccountLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["signup_available"] = signup_available()
        return context

    def get_success_url(self):
        url = super().get_success_url()
        base_path = settings.APP_BASE_PATH
        if base_path != "/":
            if url == base_path or url.startswith(base_path):
                return url
            if url.startswith("/") and not url.startswith("//"):
                return base_path.rstrip("/") + url
            return base_path
        return url


def signup_available():
    user_model = get_user_model()
    return (
        settings.SIGNUPS_ENABLED
        and user_model.objects.filter(
            is_superuser=True,
            profile__isnull=False,
            billing_account__isnull=False,
        ).exists()
        and not Conversation.objects.filter(owner__isnull=True).exists()
    )


@require_http_methods(["GET", "POST"])
def signup(request):
    if not signup_available():
        return HttpResponseNotFound("Registration is not available.")
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            user = form.save()
            profile, _ = provision_user_account(user, form.cleaned_data["display_name"])
            profile.display_name = form.cleaned_data["display_name"]
            profile.save(update_fields=("display_name", "updated_at"))
        return redirect(settings.LOGIN_URL)
    return render(request, "accounts/signup.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
def profile(request):
    own_profile = UserProfile.objects.filter(user=request.user).first()
    if own_profile is None:
        return HttpResponse("Account setup is incomplete.", status=503)
    form = ProfileForm(request.POST or None, instance=own_profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("{}profile/".format(settings.APP_BASE_PATH))
    return render(
        request,
        "accounts/profile.html",
        {"form": form, "own_profile": own_profile, "current_page": "profile"},
    )


@login_required
@require_GET
def billing(request):
    account = BillingAccount.objects.filter(user=request.user).first()
    user_profile = UserProfile.objects.filter(user=request.user).first()
    if account is None or user_profile is None:
        return HttpResponse("Account setup is incomplete.", status=503)
    return render(
        request,
        "accounts/billing.html",
        {
            "account": account,
            "display_name": user_profile.display_name or request.user.get_username(),
            "current_page": "billing",
        },
    )


@require_POST
def logout_view(request):
    logout(request)
    return redirect(settings.LOGOUT_REDIRECT_URL)


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
@api_login_required
def providers(request):
    return JsonResponse({"providers": list_model_options(), "notice": PROXY_BEHAVIOR_NOTICE})


@require_GET
@api_login_required
def conversation_list(request):
    conversations = Conversation.objects.filter(owner=request.user)[:100]
    return JsonResponse({"conversations": [_conversation_json(item) for item in conversations]})


@require_GET
@api_login_required
def conversation_detail(request, conversation_id):
    try:
        conversation = Conversation.objects.get(pk=conversation_id, owner=request.user)
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
            request.user,
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
@api_login_required
def new_message(request):
    return _submit(request)


@require_POST
@api_login_required
def conversation_message(request, conversation_id):
    return _submit(request, conversation_id)


@require_POST
@api_login_required
def retry_message(request, conversation_id):
    data = _read_json(request)
    if data is None or not isinstance(data.get("assistant_message_id"), int):
        return JsonResponse(
            {"error": {"code": "invalid_request", "message": "A response ID is required."}},
            status=400,
        )
    try:
        conversation, assistant_message = retry_failed_response(
            request.user,
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

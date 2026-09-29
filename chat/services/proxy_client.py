import json
import os
import socket
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from chat.providers import get_model_option

PROXY_BASE_URL = "https://proxy.litechat.ai"
REQUEST_TIMEOUT_SECONDS = 90
MAX_RESPONSE_BYTES = 2_000_000
MAX_OUTPUT_TOKENS = 1024


class ProxyFailure(Exception):
    def __init__(self, code, message, http_status=502):
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.conversation_id = None
        self.assistant_message_id = None


class ProxyClient:
    def generate(self, provider_id, model_id, messages, system_prompt=""):
        option = get_model_option(provider_id, model_id)
        if option is None:
            raise ProxyFailure(
                "unsupported_model",
                "That provider/model combination is not enabled.",
                http_status=400,
            )

        api_key = os.environ.get(option.key_environment_variable)
        if not api_key:
            raise ProxyFailure(
                "provider_not_configured",
                "The selected provider is not configured on the server.",
                http_status=503,
            )

        url, headers, body = self._build_request(
            provider_id,
            model_id,
            api_key,
            messages,
            system_prompt,
        )
        request = Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                payload = response.read(MAX_RESPONSE_BYTES + 1)
        except HTTPError as error:
            raise self._http_failure(error.code) from None
        except TimeoutError:
            raise ProxyFailure("proxy_timeout", "The AI service timed out.", 504) from None
        except URLError as error:
            if isinstance(error.reason, (TimeoutError, socket.timeout)):
                raise ProxyFailure("proxy_timeout", "The AI service timed out.", 504) from None
            raise ProxyFailure("proxy_unavailable", "The AI service could not be reached.", 502) from None
        except HTTPException:
            raise ProxyFailure("proxy_unavailable", "The AI service could not be reached.", 502) from None
        except OSError:
            raise ProxyFailure("proxy_unavailable", "The AI service could not be reached.", 502) from None

        if len(payload) > MAX_RESPONSE_BYTES:
            raise ProxyFailure("invalid_response", "The AI service returned an invalid response.")
        try:
            data = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ProxyFailure("invalid_response", "The AI service returned an invalid response.") from None
        return self._read_answer(provider_id, data)

    @staticmethod
    def _build_request(provider_id, model_id, api_key, messages, system_prompt=""):
        common_headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if provider_id == "openai":
            return (
                f"{PROXY_BASE_URL}/openai/v1/chat/completions",
                {**common_headers, "Authorization": f"Bearer {api_key}"},
                {
                    "model": model_id,
                    "messages": (
                        [{"role": "system", "content": system_prompt}] + messages
                        if system_prompt
                        else messages
                    ),
                    "max_tokens": MAX_OUTPUT_TOKENS,
                    "reasoning_effort": "none",
                },
            )
        if provider_id == "anthropic":
            return (
                f"{PROXY_BASE_URL}/anthropic/v1/messages",
                {
                    **common_headers,
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                },
                {
                    "model": model_id,
                    "messages": messages,
                    "max_tokens": MAX_OUTPUT_TOKENS,
                    "thinking": {"type": "disabled"},
                    **({"system": system_prompt} if system_prompt else {}),
                },
            )
        if provider_id == "google":
            contents = [
                {
                    "role": "model" if message["role"] == "assistant" else "user",
                    "parts": [{"text": message["content"]}],
                }
                for message in messages
            ]
            body = {
                "contents": contents,
                "generationConfig": {
                    "maxOutputTokens": MAX_OUTPUT_TOKENS,
                    "thinkingConfig": {"thinkingBudget": 0},
                },
            }
            if system_prompt:
                body["systemInstruction"] = {"parts": [{"text": system_prompt}]}
            return (
                f"{PROXY_BASE_URL}/google/v1beta/models/{model_id}:generateContent",
                {**common_headers, "x-goog-api-key": api_key},
                body,
            )
        raise ProxyFailure("unsupported_provider", "That provider is not enabled.", 400)

    @staticmethod
    def _read_answer(provider_id, data):
        try:
            if provider_id == "openai":
                choice = data["choices"][0]
                reason = choice["finish_reason"]
                if reason != "stop":
                    raise ProxyFailure("incomplete_response", "The AI response did not complete normally.")
                answer = choice["message"]["content"]
            elif provider_id == "anthropic":
                reason = data["stop_reason"]
                if reason != "end_turn":
                    raise ProxyFailure("incomplete_response", "The AI response did not complete normally.")
                blocks = data["content"]
                if not isinstance(blocks, list) or any(not isinstance(block, dict) for block in blocks):
                    raise ProxyFailure("invalid_response", "The AI service returned an invalid response.")
                answer = "".join(block["text"] for block in blocks if block.get("type") == "text")
            elif provider_id == "google":
                candidate = data["candidates"][0]
                reason = candidate["finishReason"]
                if reason == "SAFETY":
                    raise ProxyFailure("content_filtered", "The AI service did not return a usable response.")
                if reason != "STOP":
                    raise ProxyFailure("incomplete_response", "The AI response did not complete normally.")
                parts = candidate["content"]["parts"]
                if not isinstance(parts, list) or any(not isinstance(part, dict) for part in parts):
                    raise ProxyFailure("invalid_response", "The AI service returned an invalid response.")
                answer = "".join(part["text"] for part in parts if isinstance(part.get("text"), str))
            else:
                raise ProxyFailure("unsupported_provider", "That provider is not enabled.", 400)
        except ProxyFailure:
            raise
        except (KeyError, IndexError, TypeError):
            raise ProxyFailure("invalid_response", "The AI service returned an invalid response.") from None

        if not isinstance(answer, str) or not answer.strip():
            raise ProxyFailure("empty_response", "The AI service returned an empty response.")
        return answer

    @staticmethod
    def _http_failure(status):
        if status in (401, 403):
            return ProxyFailure(
                "provider_authentication_failed",
                "The provider key was rejected. Check the server-side configuration.",
                503,
            )
        if status == 429:
            return ProxyFailure(
                "rate_limited",
                "The AI service is rate limited. Wait before trying again.",
                429,
            )
        if status == 503:
            return ProxyFailure("proxy_unavailable", "The AI service is temporarily unavailable.", 503)
        if status == 504:
            return ProxyFailure("proxy_timeout", "The AI service timed out.", 504)
        if status in (502, 500):
            return ProxyFailure("proxy_failure", "The AI service could not complete the request.", 502)
        if status == 400:
            return ProxyFailure("proxy_rejected_request", "The AI service rejected the request.", 502)
        return ProxyFailure("proxy_failure", "The AI service could not complete the request.", 502)

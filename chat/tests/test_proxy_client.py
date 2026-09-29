import json
import os
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from django.test import SimpleTestCase

from chat.services.proxy_client import PROXY_BASE_URL, ProxyClient, ProxyFailure


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self, limit):
        return self.payload


class RawResponse(FakeResponse):
    def __init__(self, payload):
        self.payload = payload


class ProxyClientTests(SimpleTestCase):
    def test_system_prompt_uses_each_provider_native_field(self):
        messages = [{"role": "user", "content": "Hi"}]

        _, _, openai = ProxyClient._build_request(
            "openai", "gpt-5.6-luna", "key", messages, system_prompt="Be concise."
        )
        _, _, anthropic = ProxyClient._build_request(
            "anthropic", "claude-haiku-4-5-20251001", "key", messages, system_prompt="Be concise."
        )
        _, _, google = ProxyClient._build_request(
            "google", "gemini-3.8-flash", "key", messages, system_prompt="Be concise."
        )

        self.assertEqual(openai["messages"][0], {"role": "system", "content": "Be concise."})
        self.assertEqual(anthropic["system"], "Be concise.")
        self.assertEqual(google["systemInstruction"], {"parts": [{"text": "Be concise."}]})
        self.assertEqual(google["contents"], [{"role": "user", "parts": [{"text": "Hi"}]}])

    @patch.dict(os.environ, {"BUILD_OPENAI_KEY": "test-openai-key"})
    @patch("chat.services.proxy_client.urlopen")
    def test_openai_chat_completions_contract(self, urlopen):
        urlopen.return_value = FakeResponse(
            {"choices": [{"message": {"content": "Hello"}, "finish_reason": "stop"}]}
        )

        answer = ProxyClient().generate("openai", "gpt-5.6-luna", [{"role": "user", "content": "Hi"}])

        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, f"{PROXY_BASE_URL}/openai/v1/chat/completions")
        self.assertEqual(request.get_header("Authorization"), "Bearer test-openai-key")
        self.assertEqual(json.loads(request.data)["model"], "gpt-5.6-luna")
        self.assertEqual(answer, "Hello")

    @patch.dict(os.environ, {"BUILD_ANTHROPIC_KEY": "test-anthropic-key"})
    @patch("chat.services.proxy_client.urlopen")
    def test_anthropic_messages_contract(self, urlopen):
        urlopen.return_value = FakeResponse(
            {"content": [{"type": "text", "text": "Hello"}], "stop_reason": "end_turn"}
        )

        answer = ProxyClient().generate(
            "anthropic",
            "claude-haiku-4-5-20251001",
            [{"role": "user", "content": "Hi"}],
        )

        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, f"{PROXY_BASE_URL}/anthropic/v1/messages")
        self.assertEqual(request.get_header("X-api-key"), "test-anthropic-key")
        self.assertEqual(request.get_header("Anthropic-version"), "2023-06-01")
        self.assertEqual(json.loads(request.data)["max_tokens"], 1024)
        self.assertEqual(answer, "Hello")

    @patch.dict(os.environ, {"BUILD_GOOGLE_KEY": "test-google-key"})
    @patch("chat.services.proxy_client.urlopen")
    def test_google_generate_content_contract_maps_assistant_role(self, urlopen):
        urlopen.return_value = FakeResponse(
            {
                "candidates": [
                    {
                        "content": {"parts": [{"text": "Hello"}]},
                        "finishReason": "STOP",
                    }
                ]
            }
        )

        answer = ProxyClient().generate(
            "google",
            "gemini-3.8-flash",
            [
                {"role": "user", "content": "Hi"},
                {"role": "assistant", "content": "Hello"},
            ],
        )

        request = urlopen.call_args.args[0]
        self.assertEqual(
            request.full_url,
            f"{PROXY_BASE_URL}/google/v1beta/models/gemini-3.8-flash:generateContent",
        )
        self.assertEqual(request.get_header("X-goog-api-key"), "test-google-key")
        self.assertEqual(
            json.loads(request.data)["contents"],
            [
                {"role": "user", "parts": [{"text": "Hi"}]},
                {"role": "model", "parts": [{"text": "Hello"}]},
            ],
        )
        self.assertEqual(answer, "Hello")

    @patch.dict(os.environ, {}, clear=True)
    @patch("chat.services.proxy_client.urlopen")
    def test_missing_key_does_not_make_network_request(self, urlopen):
        with self.assertRaises(ProxyFailure) as raised:
            ProxyClient().generate("openai", "gpt-5.6-luna", [{"role": "user", "content": "Hi"}])

        self.assertEqual(raised.exception.code, "provider_not_configured")
        self.assertEqual(raised.exception.http_status, 503)
        urlopen.assert_not_called()

    @patch.dict(os.environ, {"BUILD_OPENAI_KEY": "test-openai-key"})
    @patch("chat.services.proxy_client.urlopen")
    def test_rate_limit_is_mapped_without_exposing_upstream_body(self, urlopen):
        urlopen.side_effect = HTTPError("url", 429, "rate limited", None, None)

        with self.assertRaises(ProxyFailure) as raised:
            ProxyClient().generate("openai", "gpt-5.6-luna", [{"role": "user", "content": "Hi"}])

        self.assertEqual(raised.exception.code, "rate_limited")
        self.assertEqual(raised.exception.http_status, 429)
        self.assertNotIn("test-openai-key", raised.exception.message)

    @patch.dict(os.environ, {"BUILD_OPENAI_KEY": "test-openai-key"})
    @patch("chat.services.proxy_client.urlopen")
    def test_incomplete_response_is_not_treated_as_success(self, urlopen):
        urlopen.return_value = FakeResponse(
            {"choices": [{"message": {"content": "Partial"}, "finish_reason": "length"}]}
        )

        with self.assertRaises(ProxyFailure) as raised:
            ProxyClient().generate("openai", "gpt-5.6-luna", [{"role": "user", "content": "Hi"}])

        self.assertEqual(raised.exception.code, "incomplete_response")

    @patch.dict(os.environ, {}, clear=True)
    @patch("chat.services.proxy_client.urlopen")
    def test_unsupported_model_is_rejected_before_network_call(self, urlopen):
        with self.assertRaises(ProxyFailure) as raised:
            ProxyClient().generate("openai", "not-a-documented-model", [{"role": "user", "content": "Hi"}])

        self.assertEqual(raised.exception.code, "unsupported_model")
        urlopen.assert_not_called()

    @patch.dict(os.environ, {"BUILD_OPENAI_KEY": "test-openai-key"})
    @patch("chat.services.proxy_client.urlopen")
    def test_auth_and_gateway_statuses_map_to_safe_errors(self, urlopen):
        expected = {
            401: ("provider_authentication_failed", 503),
            403: ("provider_authentication_failed", 503),
            500: ("proxy_failure", 502),
            502: ("proxy_failure", 502),
            503: ("proxy_unavailable", 503),
            504: ("proxy_timeout", 504),
        }
        for status, (code, http_status) in expected.items():
            with self.subTest(status=status):
                urlopen.side_effect = HTTPError("url", status, "sensitive upstream body", None, None)
                with self.assertRaises(ProxyFailure) as raised:
                    ProxyClient().generate(
                        "openai",
                        "gpt-5.6-luna",
                        [{"role": "user", "content": "Hi"}],
                    )
                self.assertEqual((raised.exception.code, raised.exception.http_status), (code, http_status))
                self.assertNotIn("sensitive upstream body", raised.exception.message)

    @patch.dict(os.environ, {"BUILD_OPENAI_KEY": "test-openai-key"})
    @patch("chat.services.proxy_client.urlopen")
    def test_malformed_response_and_transport_failures_are_sanitized(self, urlopen):
        urlopen.return_value = RawResponse(b"not json")
        with self.assertRaises(ProxyFailure) as malformed:
            ProxyClient().generate("openai", "gpt-5.6-luna", [{"role": "user", "content": "Hi"}])
        self.assertEqual(malformed.exception.code, "invalid_response")

        urlopen.side_effect = TimeoutError()
        with self.assertRaises(ProxyFailure) as timeout:
            ProxyClient().generate("openai", "gpt-5.6-luna", [{"role": "user", "content": "Hi"}])
        self.assertEqual((timeout.exception.code, timeout.exception.http_status), ("proxy_timeout", 504))

        urlopen.side_effect = URLError("sensitive network detail")
        with self.assertRaises(ProxyFailure) as unavailable:
            ProxyClient().generate("openai", "gpt-5.6-luna", [{"role": "user", "content": "Hi"}])
        self.assertEqual(unavailable.exception.code, "proxy_unavailable")
        self.assertNotIn("sensitive network detail", unavailable.exception.message)

    @patch.dict(os.environ, {"BUILD_GOOGLE_KEY": "test-google-key"})
    @patch("chat.services.proxy_client.urlopen")
    def test_google_safety_finish_is_a_safe_failure(self, urlopen):
        urlopen.return_value = FakeResponse(
            {"candidates": [{"content": {"parts": []}, "finishReason": "SAFETY"}]}
        )

        with self.assertRaises(ProxyFailure) as raised:
            ProxyClient().generate("google", "gemini-3.8-flash", [{"role": "user", "content": "Hi"}])

        self.assertEqual(raised.exception.code, "content_filtered")

import json
import os
from unittest.mock import patch

from django.test import Client, TestCase

from chat.models import Conversation, Message


class ChatViewTests(TestCase):
    @patch.dict(os.environ, {"BUILD_OPENAI_KEY": "test-openai-key"}, clear=True)
    def test_provider_catalog_lists_documented_ids_without_returning_keys(self):
        response = self.client.get("/api/providers/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(
            [item["model_id"] for item in payload["providers"]],
            ["gpt-5.6-luna", "claude-haiku-4-5-20251001", "gemini-3.8-flash"],
        )
        self.assertTrue(payload["providers"][0]["configured"])
        self.assertNotIn("test-openai-key", response.content.decode())
        self.assertNotIn("test-openai-key", self.client.get("/").content.decode())
        self.assertIn("DeepSeek Flash", payload["notice"])

    @patch("chat.services.conversations.ProxyClient.generate", return_value="A safe answer")
    def test_new_chat_and_history_can_be_reopened_and_continued(self, generate):
        new_response = self.client.post(
            "/api/messages/",
            data=json.dumps(
                {
                    "prompt": "Start here",
                    "provider_id": "openai",
                    "model_id": "gpt-5.6-luna",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(new_response.status_code, 200)
        conversation_id = new_response.json()["conversation"]["id"]

        history = self.client.get("/api/conversations/")
        detail = self.client.get(f"/api/conversations/{conversation_id}/")
        self.assertEqual(history.json()["conversations"][0]["id"], conversation_id)
        self.assertEqual(len(detail.json()["messages"]), 2)
        self.assertEqual(detail.json()["messages"][1]["content"], "A safe answer")

        follow_up = self.client.post(
            f"/api/conversations/{conversation_id}/messages/",
            data=json.dumps(
                {
                    "prompt": "Continue",
                    "provider_id": "anthropic",
                    "model_id": "claude-haiku-4-5-20251001",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(follow_up.status_code, 200)
        self.assertEqual(
            generate.call_args_list[1].args[2],
            [
                {"role": "user", "content": "Start here"},
                {"role": "assistant", "content": "A safe answer"},
                {"role": "user", "content": "Continue"},
            ],
        )
        conversation = Conversation.objects.get(pk=conversation_id)
        self.assertEqual(conversation.provider, "anthropic")
        latest_assistant = conversation.messages.filter(role=Message.Role.ASSISTANT).order_by("-created_at").first()
        self.assertEqual(latest_assistant.provider, "anthropic")

    @patch("chat.services.conversations.ProxyClient.generate")
    def test_proxy_failure_is_safe_and_prompt_is_preserved(self, generate):
        from chat.services.proxy_client import ProxyFailure

        generate.side_effect = ProxyFailure("rate_limited", "Wait before retrying.", 429)
        response = self.client.post(
            "/api/messages/",
            data=json.dumps(
                {
                    "prompt": "Keep my prompt",
                    "provider_id": "openai",
                    "model_id": "gpt-5.6-luna",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()["error"]["code"], "rate_limited")
        self.assertNotIn("traceback", response.content.decode().lower())
        self.assertEqual(Message.objects.get(role=Message.Role.USER).content, "Keep my prompt")
        self.assertEqual(Message.objects.get(role=Message.Role.ASSISTANT).status, Message.Status.FAILED)

    def test_invalid_provider_model_and_json_are_rejected(self):
        invalid_model = self.client.post(
            "/api/messages/",
            data=json.dumps({"prompt": "Hello", "provider_id": "openai", "model_id": "unknown"}),
            content_type="application/json",
        )
        invalid_json = self.client.post("/api/messages/", data="not json", content_type="application/json")

        self.assertEqual(invalid_model.status_code, 400)
        self.assertEqual(invalid_model.json()["error"]["code"], "unsupported_model")
        self.assertEqual(invalid_json.status_code, 400)
        self.assertEqual(Conversation.objects.count(), 0)

    @patch.dict(os.environ, {"BUILD_OPENAI_KEY": "test-openai-key"}, clear=True)
    @patch("chat.services.conversations.ProxyClient.generate", return_value="Answer")
    def test_post_requires_csrf_token(self, generate):
        client = Client(enforce_csrf_checks=True)
        page = client.get("/")
        token = client.cookies["csrftoken"].value
        body = json.dumps(
            {"prompt": "Hello", "provider_id": "openai", "model_id": "gpt-5.6-luna"}
        )

        rejected = client.post("/api/messages/", data=body, content_type="application/json")
        accepted = client.post(
            "/api/messages/",
            data=body,
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertEqual(page.status_code, 200)
        self.assertEqual(rejected.status_code, 403)
        self.assertEqual(accepted.status_code, 200)
        generate.assert_called_once()

    @patch.dict(os.environ, {}, clear=True)
    @patch("chat.services.proxy_client.urlopen")
    def test_missing_key_returns_safe_error_without_network_call(self, urlopen):
        response = self.client.post(
            "/api/messages/",
            data=json.dumps(
                {
                    "prompt": "Preserve this",
                    "provider_id": "openai",
                    "model_id": "gpt-5.6-luna",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"]["code"], "provider_not_configured")
        self.assertEqual(Message.objects.get(role=Message.Role.USER).content, "Preserve this")
        self.assertNotIn("BUILD_OPENAI_KEY", response.content.decode())
        urlopen.assert_not_called()

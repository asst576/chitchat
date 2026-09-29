import json
import os
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from chat.models import Conversation, Message, UserProfile


class ChatViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="chat-user", password="StrongPassword123!")
        self.client.force_login(self.user)

    def test_workspace_asset_urls_are_relative_to_the_proxy_mount(self):
        response = self.client.get("/")
        html = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(settings.STATIC_URL, "/static/")
        self.assertContains(response, "ChitChat")
        self.assertNotContains(response, "LiteChat")
        self.assertContains(response, "Hi, <strong>chat-user</strong>!", html=True)
        self.assertIn('<body class="chat-page">', html)
        self.assertIn('<div class="app-shell chat-app">', html)
        self.assertIn('<main class="workspace chat-workspace">', html)
        self.assertIn('<base href="/">', html)
        self.assertIn('href="static/chat/chat.css"', html)
        self.assertIn('src="static/chat/markdown.js" defer', html)
        self.assertIn('src="static/chat/chat.js"', html)
        self.assertLess(html.index("static/chat/markdown.js"), html.index("static/chat/chat.js"))
        self.assertIn('action="/accounts/logout/"', html)
        javascript = (settings.BASE_DIR / "static" / "chat" / "chat.js").read_text(encoding="utf-8")
        stylesheet = (settings.BASE_DIR / "static" / "chat" / "chat.css").read_text(encoding="utf-8")
        self.assertIn('new URL("api", document.baseURI)', javascript)
        self.assertIn('message.role === "assistant" ? "ChitChat" : "You"', javascript)
        self.assertIn("window.location.assign(new URL(loginUrl, document.baseURI));", javascript)
        self.assertIn('message.role === "assistant" ? "C" : "Y"', javascript)
        self.assertIn("body.chat-page { height: 100vh; height: 100dvh; overflow: hidden; }", stylesheet)
        self.assertIn(".chat-app { height: 100vh; height: 100dvh;", stylesheet)
        self.assertIn(".chat-sidebar { height: 100vh; height: 100dvh;", stylesheet)
        self.assertIn(".chat-workspace { height: 100vh; height: 100dvh; min-height: 0; overflow: hidden; }", stylesheet)
        self.assertIn(".chat-workspace .topbar, .chat-workspace .status-line { flex: 0 0 auto; }", stylesheet)
        self.assertIn(".chat-workspace .conversation-area { flex: 1 1 auto; min-height: 0; overflow-x: hidden; overflow-y: auto;", stylesheet)
        self.assertIn(".chat-workspace .message-list { padding-bottom: 72px; }", stylesheet)
        self.assertIn(".chat-workspace .composer-wrap { flex: 0 0 auto; }", stylesheet)
        self.assertIn("overflow-wrap: anywhere;", stylesheet)
        self.assertIn(".chat-app { grid-template-rows: auto minmax(0, 1fr); }", stylesheet)
        self.assertIn("max-width: 44vw;", stylesheet)
        self.assertIn("@media (max-width: 760px)", stylesheet)
        self.assertIn(".account-nav { display: flex; grid-column: 1 / -1;", stylesheet)
        order = [
            html.index('class="wordmark"'),
            html.index("Hi, <strong>chat-user</strong>!"),
            html.index('id="new-chat"'),
            html.index('aria-label="Account navigation"'),
            html.index("RECENT"),
        ]
        self.assertEqual(order, sorted(order))

    def test_sidebar_prefers_non_empty_profile_display_name(self):
        UserProfile.objects.create(user=self.user, display_name="Chat Friend")

        response = self.client.get("/")

        self.assertContains(response, "Hi, <strong>Chat Friend</strong>!", html=True)
        self.assertNotContains(response, "Hi, <strong>chat-user</strong>!", html=True)

    def test_blank_profile_display_name_falls_back_to_username(self):
        UserProfile.objects.create(user=self.user, display_name="")

        response = self.client.get("/")

        self.assertContains(response, "Hi, <strong>chat-user</strong>!", html=True)

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
        self.assertEqual(conversation.owner, self.user)
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
        client.force_login(self.user)
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

    def test_anonymous_workspace_and_api_access_are_protected(self):
        client = Client()

        page = client.get("/")
        provider_response = client.get("/api/providers/")
        response = client.get("/api/conversations/")
        write_response = client.post(
            "/api/messages/",
            data=json.dumps({"prompt": "blocked"}),
            content_type="application/json",
        )

        self.assertEqual(page.status_code, 302)
        self.assertTrue(page["Location"].startswith("/accounts/login/?next="))
        for api_response in (provider_response, response, write_response):
            self.assertEqual(api_response.status_code, 401)
            self.assertEqual(api_response.json()["error"]["code"], "authentication_required")
        self.assertEqual(client.get("/profile/").status_code, 302)
        self.assertEqual(client.get("/billing/").status_code, 302)

    def test_system_prompt_is_not_in_chat_page_or_provider_catalog(self):
        secret_prompt = "This account-only instruction must not reach the browser."
        UserProfile.objects.create(user=self.user, system_prompt=secret_prompt)

        page = self.client.get("/")
        catalog = self.client.get("/api/providers/")

        self.assertNotContains(page, secret_prompt)
        self.assertNotContains(catalog, secret_prompt)

    @patch("chat.services.conversations.ProxyClient.generate", return_value="Private answer")
    def test_history_and_conversation_apis_are_owner_scoped(self, generate):
        created = self.client.post(
            "/api/messages/",
            data=json.dumps(
                {
                    "prompt": "My thread",
                    "provider_id": "openai",
                    "model_id": "gpt-5.6-luna",
                    "owner_id": 99999,
                }
            ),
            content_type="application/json",
        )
        conversation_id = created.json()["conversation"]["id"]
        other = get_user_model().objects.create_user(username="other-viewer", password="StrongPassword123!")
        other_client = Client()
        other_client.force_login(other)

        history = other_client.get("/api/conversations/")
        foreign_detail = other_client.get(f"/api/conversations/{conversation_id}/")
        unknown_detail = other_client.get("/api/conversations/00000000-0000-0000-0000-000000000001/")
        foreign_continue = other_client.post(
            f"/api/conversations/{conversation_id}/messages/",
            data=json.dumps(
                {"prompt": "Intrude", "provider_id": "openai", "model_id": "gpt-5.6-luna"}
            ),
            content_type="application/json",
        )

        self.assertEqual(created.status_code, 200)
        self.assertEqual(Conversation.objects.get(pk=conversation_id).owner, self.user)
        self.assertEqual(history.json(), {"conversations": []})
        self.assertEqual(foreign_detail.status_code, 404)
        self.assertEqual(foreign_detail.json(), unknown_detail.json())
        self.assertEqual(foreign_continue.status_code, 404)
        self.assertEqual(foreign_continue.json()["error"]["code"], "conversation_not_found")
        self.assertEqual(generate.call_count, 1)

    def test_foreign_retry_and_unknown_retry_return_the_same_not_found_response(self):
        other = get_user_model().objects.create_user(username="retry-viewer", password="StrongPassword123!")
        conversation = Conversation.objects.create(
            owner=self.user,
            title="Private failed thread",
            provider="openai",
            model_id="gpt-5.6-luna",
        )
        Message.objects.create(conversation=conversation, role=Message.Role.USER, content="Original prompt")
        failed = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="",
            status=Message.Status.FAILED,
            provider="openai",
            model_id="gpt-5.6-luna",
        )
        client = Client()
        client.force_login(other)
        payload = json.dumps({"assistant_message_id": failed.pk})

        foreign = client.post(
            f"/api/conversations/{conversation.pk}/retry/",
            data=payload,
            content_type="application/json",
        )
        missing = client.post(
            "/api/conversations/00000000-0000-0000-0000-000000000001/retry/",
            data=payload,
            content_type="application/json",
        )

        self.assertEqual((foreign.status_code, missing.status_code), (404, 404))
        self.assertEqual(foreign.json(), missing.json())
        self.assertEqual(Message.objects.get(pk=failed.pk).status, Message.Status.FAILED)

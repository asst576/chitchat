from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from chat.models import Conversation, Message, UserProfile
from chat.services.conversations import ChatError, retry_failed_response, submit_prompt
from chat.services.proxy_client import ProxyFailure


class ConversationServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="service-user", password="StrongPassword123!")

    @patch("chat.services.conversations.ProxyClient.generate")
    def test_context_is_reconstructed_from_completed_messages(self, generate):
        generate.side_effect = ["First reply", "Second reply"]

        conversation, _ = submit_prompt(self.user, "First prompt", "openai", "gpt-5.6-luna")
        submit_prompt(self.user, "Follow-up", "openai", "gpt-5.6-luna", conversation.pk)

        first_context = generate.call_args_list[0].args[2]
        second_context = generate.call_args_list[1].args[2]
        self.assertEqual(first_context, [{"role": "user", "content": "First prompt"}])
        self.assertEqual(
            second_context,
            [
                {"role": "user", "content": "First prompt"},
                {"role": "assistant", "content": "First reply"},
                {"role": "user", "content": "Follow-up"},
            ],
        )
        conversation.refresh_from_db()
        self.assertEqual(conversation.title, "First prompt")
        self.assertEqual(conversation.messages.count(), 4)

    @patch("chat.services.conversations.ProxyClient.generate")
    def test_failed_response_is_saved_and_retry_does_not_duplicate_prompt(self, generate):
        generate.side_effect = [
            ProxyFailure("rate_limited", "The AI service is rate limited.", 429),
            "Recovered reply",
        ]

        with self.assertRaises(ProxyFailure) as raised:
            submit_prompt(self.user, "Keep this prompt", "anthropic", "claude-haiku-4-5-20251001")

        conversation = Conversation.objects.get(pk=raised.exception.conversation_id)
        assistant = conversation.messages.get(role=Message.Role.ASSISTANT)
        self.assertEqual(assistant.status, Message.Status.FAILED)
        self.assertEqual(conversation.messages.filter(role=Message.Role.USER).count(), 1)

        _, retried = retry_failed_response(self.user, conversation.pk, assistant.pk)

        self.assertEqual(retried.status, Message.Status.COMPLETED)
        self.assertEqual(retried.content, "Recovered reply")
        self.assertEqual(conversation.messages.filter(role=Message.Role.USER).count(), 1)
        self.assertEqual(
            generate.call_args_list[1].args[2],
            [{"role": "user", "content": "Keep this prompt"}],
        )

    def test_prompt_and_selection_validation(self):
        with self.assertRaises(ChatError) as empty:
            submit_prompt(self.user, "  ", "openai", "gpt-5.6-luna")
        self.assertEqual(empty.exception.code, "empty_prompt")

        with self.assertRaises(ChatError) as invalid_model:
            submit_prompt(self.user, "Hello", "openai", "unverified-model")
        self.assertEqual(invalid_model.exception.code, "unsupported_model")
        self.assertEqual(Conversation.objects.count(), 0)

    @patch("chat.services.conversations.ProxyClient.generate")
    def test_failed_turn_is_excluded_from_later_context(self, generate):
        generate.side_effect = [
            "First reply",
            ProxyFailure("proxy_timeout", "Timed out.", 504),
            "Third reply",
        ]
        conversation, _ = submit_prompt(self.user, "First", "openai", "gpt-5.6-luna")
        with self.assertRaises(ProxyFailure):
            submit_prompt(self.user, "Failed follow-up", "openai", "gpt-5.6-luna", conversation.pk)
        submit_prompt(self.user, "Next follow-up", "openai", "gpt-5.6-luna", conversation.pk)

        self.assertEqual(
            generate.call_args_list[2].args[2],
            [
                {"role": "user", "content": "First"},
                {"role": "assistant", "content": "First reply"},
                {"role": "user", "content": "Next follow-up"},
            ],
        )

    @patch("chat.services.conversations.ProxyClient.generate", return_value="Answer")
    def test_other_users_cannot_continue_a_conversation(self, generate):
        conversation, _ = submit_prompt(self.user, "Private", "openai", "gpt-5.6-luna")
        other_user = get_user_model().objects.create_user(username="other", password="StrongPassword123!")

        with self.assertRaises(ChatError) as raised:
            submit_prompt(other_user, "Intrude", "openai", "gpt-5.6-luna", conversation.pk)

        self.assertEqual((raised.exception.code, raised.exception.http_status), ("conversation_not_found", 404))
        self.assertEqual(conversation.messages.count(), 2)
        self.assertEqual(generate.call_count, 1)

    @patch("chat.services.conversations.ProxyClient.generate", return_value="Answer")
    def test_profile_prompt_applies_to_future_turns_without_entering_transcript(self, generate):
        profile = UserProfile.objects.create(user=self.user, system_prompt="First instruction")
        conversation, _ = submit_prompt(self.user, "First", "openai", "gpt-5.6-luna")
        profile.system_prompt = "Updated instruction"
        profile.save(update_fields=("system_prompt", "updated_at"))
        submit_prompt(self.user, "Follow-up", "openai", "gpt-5.6-luna", conversation.pk)

        self.assertEqual(generate.call_args_list[0].kwargs["system_prompt"], "First instruction")
        self.assertEqual(generate.call_args_list[1].kwargs["system_prompt"], "Updated instruction")
        self.assertEqual(conversation.messages.count(), 4)
        self.assertFalse(conversation.messages.filter(content__contains="instruction").exists())

        other_user = get_user_model().objects.create_user(username="prompt-isolation", password="StrongPassword123!")
        submit_prompt(other_user, "Separate account", "openai", "gpt-5.6-luna")
        self.assertEqual(generate.call_args_list[2].kwargs["system_prompt"], "")

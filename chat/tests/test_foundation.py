from django.db import IntegrityError, transaction
from django.test import TestCase

from chat.models import Conversation, Message


class WorkspaceFoundationTests(TestCase):
    def test_home_page_renders_workspace(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "LiteChat")
        self.assertContains(response, "New conversation")

    def test_health_check_returns_ok(self):
        response = self.client.get("/healthz/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_conversation_delete_cascades_to_messages(self):
        conversation = Conversation.objects.create(
            title="A thread",
            provider="openai",
            model_id="gpt-5.6-luna",
        )
        first = Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content="Prompt",
        )
        second = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="Reply",
            provider="openai",
            model_id="gpt-5.6-luna",
        )

        self.assertEqual(list(conversation.messages.all()), [first, second])
        conversation.delete()
        self.assertEqual(Message.objects.count(), 0)

    def test_message_role_is_constrained_in_database(self):
        conversation = Conversation.objects.create(
            title="A thread",
            provider="openai",
            model_id="gpt-5.6-luna",
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            Message.objects.create(
                conversation=conversation,
                role="system",
                content="Not an allowed role",
            )

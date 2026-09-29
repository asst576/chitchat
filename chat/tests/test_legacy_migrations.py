from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase, override_settings

from chat.models import BillingAccount, Conversation, Message
from chat.views import signup_available

MIGRATION_3 = "0003_billingaccount_userprofile_conversation_owner_and_more"
MIGRATION_4 = "0004_require_conversation_owner"


class LegacyConversationMigrationTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        super().setUp()
        self.latest_targets = MigrationExecutor(connection).loader.graph.leaf_nodes()
        MigrationExecutor(connection).migrate([("chat", MIGRATION_3)])
        old_apps = MigrationExecutor(connection).loader.project_state([("chat", MIGRATION_3)]).apps
        old_conversation = old_apps.get_model("chat", "Conversation")
        old_message = old_apps.get_model("chat", "Message")
        self.legacy_id = old_conversation.objects.create(
            title="Legacy thread",
            provider="openai",
            model_id="gpt-5.6-luna",
        ).pk
        old_message.objects.create(conversation_id=self.legacy_id, role="user", content="Original prompt")
        old_message.objects.create(
            conversation_id=self.legacy_id,
            role="assistant",
            content="Original reply",
            provider="openai",
            model_id="gpt-5.6-luna",
        )
        self.bootstrap = get_user_model().objects.create_superuser(
            username="bootstrap-admin",
            email="bootstrap@example.invalid",
            password=None,
        )

    def tearDown(self):
        MigrationExecutor(connection).migrate(self.latest_targets)
        super().tearDown()

    @override_settings(SIGNUPS_ENABLED=True)
    def test_legacy_owner_command_requires_explicit_superuser_and_preserves_chat(self):
        with self.assertRaises(CommandError):
            call_command("assign_legacy_conversation_owner", stdout=StringIO())

        self.assertIsNone(Conversation.objects.get(pk=self.legacy_id).owner_id)
        self.assertFalse(signup_available())
        with self.assertRaisesRegex(RuntimeError, "unowned conversation"):
            MigrationExecutor(connection).migrate([("chat", MIGRATION_4)])

        output = StringIO()
        call_command(
            "provision_bootstrap_account",
            username=self.bootstrap.username,
            stdout=output,
        )
        call_command(
            "provision_bootstrap_account",
            username=self.bootstrap.username,
            stdout=StringIO(),
        )
        self.assertFalse(signup_available())
        call_command(
            "assign_legacy_conversation_owner",
            username=self.bootstrap.username,
            stdout=output,
        )
        self.assertTrue(signup_available())
        MigrationExecutor(connection).migrate([("chat", MIGRATION_4)])

        conversation = Conversation.objects.get(pk=self.legacy_id)
        self.assertEqual(conversation.owner, self.bootstrap)
        self.assertEqual((conversation.title, conversation.provider, conversation.model_id), (
            "Legacy thread",
            "openai",
            "gpt-5.6-luna",
        ))
        self.assertEqual(
            list(conversation.messages.values_list("content", flat=True)),
            ["Original prompt", "Original reply"],
        )
        self.assertEqual(BillingAccount.objects.filter(user=self.bootstrap).count(), 1)
        self.assertIn("Assigned 1 legacy conversation", output.getvalue())

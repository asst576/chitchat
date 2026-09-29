import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def require_owned_conversations(apps, schema_editor):
    Conversation = apps.get_model("chat", "Conversation")
    unowned_count = Conversation.objects.using(schema_editor.connection.alias).filter(owner__isnull=True).count()
    if unowned_count:
        raise RuntimeError(
            "Cannot require conversation owners while {} unowned conversation(s) remain. "
            "Create the designated bootstrap superuser, provision its account, run "
            "assign_legacy_conversation_owner --username <bootstrap-admin>, verify the data, "
            "then retry this migration.".format(unowned_count)
        )


class Migration(migrations.Migration):
    dependencies = [
        ("chat", "0003_billingaccount_userprofile_conversation_owner_and_more"),
    ]

    operations = [
        migrations.RunPython(require_owned_conversations, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="conversation",
            name="owner",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="conversations",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]

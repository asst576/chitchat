from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from chat.models import Conversation


class Command(BaseCommand):
    help = "Assign unowned legacy conversations to an explicitly designated bootstrap superuser."

    def add_arguments(self, parser):
        parser.add_argument("--username")

    def handle(self, *args, **options):
        with transaction.atomic():
            unowned = Conversation.objects.filter(owner__isnull=True)
            count = unowned.count()
            if count == 0:
                self.stdout.write("No unowned conversations found.")
                return
            username = options["username"]
            if not username:
                raise CommandError("Unowned conversations exist; supply the bootstrap --username explicitly.")
            try:
                user = get_user_model().objects.get(username=username)
            except get_user_model().DoesNotExist:
                raise CommandError("The designated bootstrap username does not exist.") from None
            if not user.is_superuser:
                raise CommandError("The designated bootstrap account must be a superuser.")

            assigned = unowned.update(owner=user)
            if assigned != count:
                raise CommandError("The number of assigned conversations changed during the operation.")

        self.stdout.write(
            self.style.SUCCESS(
                "Assigned {} legacy conversation(s) to {} without changing messages.".format(
                    assigned,
                    user.get_username(),
                )
            )
        )

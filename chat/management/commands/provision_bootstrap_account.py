from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from chat.services.accounts import provision_user_account


class Command(BaseCommand):
    help = "Create the profile and personal billing account for a designated superuser."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)

    def handle(self, *args, **options):
        try:
            user = get_user_model().objects.get(username=options["username"])
        except get_user_model().DoesNotExist:
            raise CommandError("The designated bootstrap username does not exist.") from None
        if not user.is_superuser:
            raise CommandError("The designated bootstrap account must be a superuser.")

        provision_user_account(user)
        self.stdout.write(
            self.style.SUCCESS(
                "Provisioned profile and personal billing account for {}.".format(user.get_username())
            )
        )

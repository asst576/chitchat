from django.db import transaction

from chat.models import BillingAccount, UserProfile


@transaction.atomic
def provision_user_account(user, display_name=""):
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={"display_name": display_name},
    )
    billing_account, _ = BillingAccount.objects.get_or_create(user=user)
    return profile, billing_account

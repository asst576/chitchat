import os
import subprocess
import sys
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import Client, TestCase, override_settings

from chat.models import BillingAccount, UserProfile
from chat.services.accounts import provision_user_account

PASSWORD = "cinder-fig-74!Maple"


class AccountViewTests(TestCase):
    def make_superuser(self, username="bootstrap"):
        user = get_user_model().objects.create_superuser(username=username, password=PASSWORD)
        provision_user_account(user)
        return user

    @override_settings(SIGNUPS_ENABLED=True)
    def test_signup_waits_for_operator_bootstrap_account(self):
        response = self.client.get("/accounts/signup/")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(get_user_model().objects.count(), 0)

    @override_settings(SIGNUPS_ENABLED=True)
    def test_signup_waits_until_bootstrap_account_is_provisioned(self):
        get_user_model().objects.create_superuser(username="unprovisioned", password=PASSWORD)

        response = self.client.get("/accounts/signup/")

        self.assertEqual(response.status_code, 404)

    @override_settings(SIGNUPS_ENABLED=True)
    def test_signup_creates_hashed_user_profile_and_personal_account(self):
        self.make_superuser()
        signup_page = self.client.get("/accounts/signup/")
        response = self.client.post(
            "/accounts/signup/",
            {
                "username": "new-member",
                "display_name": "New Member",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )

        self.assertRedirects(response, "/accounts/login/")
        login_page = self.client.get("/accounts/login/")
        for page in (signup_page, login_page):
            self.assertContains(page, "ChitChat")
            self.assertNotContains(page, "LiteChat")
        user = get_user_model().objects.get(username="new-member")
        self.assertNotEqual(user.password, PASSWORD)
        self.assertTrue(user.check_password(PASSWORD))
        self.assertEqual(UserProfile.objects.filter(user=user).count(), 1)
        self.assertEqual(BillingAccount.objects.filter(user=user).count(), 1)
        self.assertEqual(user.profile.display_name, "New Member")
        account = user.billing_account
        self.assertEqual(
            (account.account_name, account.currency_code, account.status, account.available_credit),
            ("Personal", "USD", BillingAccount.Status.ACTIVE, Decimal("2.00")),
        )

    @override_settings(SIGNUPS_ENABLED=True)
    def test_signup_validates_duplicate_username_password_confirmation_and_strength(self):
        self.make_superuser()
        get_user_model().objects.create_user(username="taken", password=PASSWORD)

        duplicate = self.client.post(
            "/accounts/signup/",
            {"username": "taken", "password1": PASSWORD, "password2": PASSWORD},
        )
        mismatch = self.client.post(
            "/accounts/signup/",
            {"username": "different", "password1": PASSWORD, "password2": PASSWORD + "x"},
        )
        weak = self.client.post(
            "/accounts/signup/",
            {"username": "weak", "password1": "1234", "password2": "1234"},
        )

        self.assertEqual(duplicate.status_code, 200)
        self.assertContains(duplicate, "A user with that username already exists")
        self.assertEqual(mismatch.status_code, 200)
        self.assertContains(mismatch, "The two password fields")
        self.assertEqual(weak.status_code, 200)
        self.assertFalse(get_user_model().objects.filter(username__in=("different", "weak")).exists())

    @override_settings(SIGNUPS_ENABLED=True)
    def test_signup_rolls_back_user_if_related_account_provisioning_fails(self):
        self.make_superuser()

        with patch("chat.views.provision_user_account", side_effect=RuntimeError("provisioning failed")):
            with self.assertRaises(RuntimeError):
                self.client.post(
                    "/accounts/signup/",
                    {
                        "username": "rolled-back",
                        "password1": PASSWORD,
                        "password2": PASSWORD,
                    },
                )

        self.assertFalse(get_user_model().objects.filter(username="rolled-back").exists())

    def test_login_logout_and_private_page_session_lifecycle(self):
        user = get_user_model().objects.create_user(username="member", password=PASSWORD)
        bad_login = self.client.post("/accounts/login/", {"username": "member", "password": "wrong"})
        login_response = self.client.post("/accounts/login/", {"username": "member", "password": PASSWORD})
        private_page = self.client.get("/")
        logout_response = self.client.post("/accounts/logout/")
        logged_out_page = self.client.get("/")

        self.assertEqual(bad_login.status_code, 200)
        self.assertContains(bad_login, "Please enter a correct username and password")
        self.assertNotContains(bad_login, "Create an account")
        self.assertNotContains(bad_login, "Hi, ")
        self.assertEqual(login_response.status_code, 302)
        self.assertEqual(login_response["Location"], "/")
        self.assertEqual(private_page.status_code, 200)
        self.assertRedirects(logout_response, "/accounts/login/")
        self.assertEqual(logged_out_page.status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertTrue(user.pk)

    def test_login_next_redirect_only_accepts_same_origin_urls(self):
        user = get_user_model().objects.create_user(username="redirect-member", password=PASSWORD)

        safe_client = Client()
        safe = safe_client.post(
            "/accounts/login/?next=/billing/",
            {"username": user.username, "password": PASSWORD, "next": "/billing/"},
        )
        unsafe = Client().post(
            "/accounts/login/?next=https://attacker.example/",
            {"username": user.username, "password": PASSWORD, "next": "https://attacker.example/"},
        )

        self.assertEqual(safe["Location"], "/billing/")
        self.assertEqual(unsafe["Location"], "/")

    def test_logout_requires_post_and_csrf(self):
        user = get_user_model().objects.create_user(username="csrf-member", password=PASSWORD)
        client = Client(enforce_csrf_checks=True)
        client.force_login(user)

        page = client.get("/")
        token = client.cookies["csrftoken"].value
        rejected = client.post("/accounts/logout/")
        accepted = client.post("/accounts/logout/", HTTP_X_CSRFTOKEN=token)
        get_logout = self.client.get("/accounts/logout/")

        self.assertEqual(page.status_code, 200)
        self.assertEqual(rejected.status_code, 403)
        self.assertRedirects(accepted, "/accounts/login/")
        self.assertEqual(get_logout.status_code, 405)

    def test_profile_updates_only_approved_fields_and_billing_is_read_only(self):
        user = get_user_model().objects.create_user(username="profile-member", password=PASSWORD)
        provision_user_account(user)
        self.client.force_login(user)
        before = user.date_joined

        profile_page = self.client.get("/profile/")
        saved = self.client.post(
            "/profile/",
            {
                "display_name": "A New Name",
                "system_prompt": "Keep my instructions private.",
                "username": "changed-username",
                "user_id": "99999",
                "is_superuser": "on",
            },
        )
        user.refresh_from_db()
        billing_page = self.client.get("/billing/")
        billing_post = self.client.post("/billing/", {"available_credit": "9999"})

        self.assertEqual(profile_page.status_code, 200)
        self.assertContains(profile_page, "ChitChat")
        self.assertContains(profile_page, str(user.pk))
        self.assertContains(profile_page, "Member since")
        self.assertRedirects(saved, "/profile/")
        self.assertEqual(user.username, "profile-member")
        self.assertFalse(user.is_superuser)
        self.assertEqual(user.date_joined, before)
        self.assertEqual(user.profile.display_name, "A New Name")
        self.assertEqual(user.profile.system_prompt, "Keep my instructions private.")
        self.assertEqual(billing_page.status_code, 200)
        self.assertContains(billing_page, "ChitChat")
        self.assertContains(billing_page, "[Personal] A New Name")
        self.assertContains(billing_page, "USD $2.00")
        self.assertEqual(billing_post.status_code, 405)
        self.assertEqual(user.billing_account.available_credit, Decimal("2.00"))

    def test_profile_and_billing_reads_do_not_provision_missing_records(self):
        user = get_user_model().objects.create_user(username="unprovisioned-member", password=PASSWORD)
        self.client.force_login(user)

        profile_response = self.client.get("/profile/")
        billing_response = self.client.get("/billing/")

        self.assertEqual(profile_response.status_code, 503)
        self.assertEqual(billing_response.status_code, 503)
        self.assertFalse(UserProfile.objects.filter(user=user).exists())
        self.assertFalse(BillingAccount.objects.filter(user=user).exists())

    def test_billing_balance_cannot_be_negative(self):
        user = get_user_model().objects.create_user(username="billing-member", password=PASSWORD)
        account = BillingAccount.objects.create(user=user)

        with self.assertRaises(IntegrityError), transaction.atomic():
            BillingAccount.objects.filter(pk=account.pk).update(available_credit=Decimal("-0.01"))

    @override_settings(APP_BASE_PATH="/proxy/5001/")
    def test_mount_prefix_is_used_for_account_assets_navigation_and_login_redirect(self):
        anonymous = Client().get("/")
        user = get_user_model().objects.create_user(username="mounted", password=PASSWORD)
        self.client.force_login(user)
        page = self.client.get("/")

        self.assertEqual(anonymous["Location"], "/accounts/login/?next=/")
        page_html = page.content.decode()
        self.assertIn('<base href="/proxy/5001/">', page_html)
        self.assertIn('action="/proxy/5001/accounts/logout/"', page_html)
        self.assertIn('data-login-url="/proxy/5001/accounts/login/"', page_html)

    @override_settings(
        APP_BASE_PATH="/proxy/5001/",
        LOGIN_URL="/accounts/login/",
        LOGIN_REDIRECT_URL="/",
        LOGOUT_REDIRECT_URL="/accounts/login/",
    )
    def test_login_next_redirect_is_normalized_for_the_proxy_mount(self):
        user = get_user_model().objects.create_user(username="mounted-login", password=PASSWORD)
        outside_mount = Client().post(
            "/accounts/login/?next=/billing/",
            {"username": user.username, "password": PASSWORD, "next": "/billing/"},
        )
        inside_mount = Client().post(
            "/accounts/login/?next=/proxy/5001/profile/",
            {"username": user.username, "password": PASSWORD, "next": "/proxy/5001/profile/"},
        )

        self.assertEqual(outside_mount["Location"], "/billing/")
        self.assertEqual(inside_mount["Location"], "/profile/")

    def test_mount_environment_keeps_auth_location_paths_upstream_relative(self):
        env = os.environ.copy()
        env.update(
            DJANGO_DEBUG="true",
            DJANGO_SETTINGS_MODULE="config.settings",
            DJANGO_APP_BASE_PATH="/proxy/5001/",
        )
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from django.conf import settings; print('|'.join((settings.APP_BASE_PATH, settings.LOGIN_URL, settings.LOGIN_REDIRECT_URL, settings.LOGOUT_REDIRECT_URL)))",
            ],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )

        self.assertEqual(
            result.stdout.strip(),
            "/proxy/5001/|/accounts/login/|/|/accounts/login/",
        )

    @override_settings(
        APP_BASE_PATH="/proxy/5001/",
        LOGIN_URL="/accounts/login/",
        LOGIN_REDIRECT_URL="/",
        LOGOUT_REDIRECT_URL="/accounts/login/",
        SIGNUPS_ENABLED=True,
    )
    def test_code_range_script_prefix_is_added_once_to_auth_routes(self):
        self.make_superuser()
        mount = "/proxy/5001/"
        script_name = mount.rstrip("/")
        anonymous = Client()

        def external_location(upstream_location):
            path, separator, query = upstream_location.partition("?")
            return mount.rstrip("/") + path + (separator + query if separator else "")

        chat_redirect = anonymous.get("/", SCRIPT_NAME=script_name)
        self.assertEqual(chat_redirect["Location"], "/accounts/login/?next=/proxy/5001/")
        external_login_url = external_location(chat_redirect["Location"])
        self.assertEqual(
            external_login_url.split("?", 1)[0],
            "/proxy/5001/accounts/login/",
        )
        self.assertNotIn("/proxy/5001/proxy/5001/", external_login_url)

        signup_page = anonymous.get("/accounts/signup/", SCRIPT_NAME=script_name)
        self.assertEqual(signup_page.status_code, 200)
        self.assertIn('action="/proxy/5001/accounts/signup/"', signup_page.content.decode())

        signup = anonymous.post(
            "/accounts/signup/",
            {
                "username": "mounted-signup",
                "display_name": "Mounted Member",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
            SCRIPT_NAME=script_name,
        )
        self.assertEqual(signup.status_code, 302)
        self.assertEqual(signup["Location"], "/accounts/login/")
        self.assertEqual(external_location(signup["Location"]), "/proxy/5001/accounts/login/")

        member = Client()
        login = member.post(
            "/accounts/login/?next=/proxy/5001/profile/",
            {"username": "mounted-signup", "password": PASSWORD},
            SCRIPT_NAME=script_name,
        )
        self.assertEqual(login.status_code, 302)
        self.assertEqual(login["Location"], "/profile/")
        self.assertEqual(external_location(login["Location"]), "/proxy/5001/profile/")

        profile_page = member.get("/profile/", SCRIPT_NAME=script_name)
        billing_page = member.get("/billing/", SCRIPT_NAME=script_name)
        self.assertEqual((profile_page.status_code, billing_page.status_code), (200, 200))
        self.assertIn("Hi, <strong>Mounted Member</strong>!", profile_page.content.decode())
        self.assertIn('action="/proxy/5001/profile/"', profile_page.content.decode())
        self.assertIn('href="/proxy/5001/billing/"', profile_page.content.decode())
        self.assertIn("[Personal] Mounted Member", billing_page.content.decode())
        self.assertNotIn("/proxy/5001/proxy/5001/", profile_page.content.decode())
        self.assertNotIn("/proxy/5001/proxy/5001/", billing_page.content.decode())

        profile_save = member.post(
            "/profile/",
            {"display_name": "Updated Member", "system_prompt": "Be brief."},
            SCRIPT_NAME=script_name,
        )
        self.assertEqual(profile_save.status_code, 302)
        self.assertEqual(external_location(profile_save["Location"]), "/proxy/5001/profile/")
        self.assertEqual(member.get("/billing/", SCRIPT_NAME=script_name).status_code, 200)
        chat_page = member.get("/", SCRIPT_NAME=script_name)
        self.assertEqual(chat_page.status_code, 200)
        chat_html = chat_page.content.decode()
        self.assertIn("Hi, <strong>Updated Member</strong>!", chat_html)
        self.assertIn('class="app-shell chat-app"', chat_html)
        self.assertIn('class="workspace chat-workspace"', chat_html)
        self.assertIn('<base href="/proxy/5001/">', chat_html)
        self.assertIn('href="static/chat/chat.css"', chat_html)
        self.assertIn('href="/proxy/5001/"', chat_html)
        self.assertIn('href="/proxy/5001/profile/"', chat_html)
        self.assertIn('href="/proxy/5001/billing/"', chat_html)
        self.assertEqual(member.get("/api/conversations/", SCRIPT_NAME=script_name).status_code, 200)

        logout = member.post("/accounts/logout/", SCRIPT_NAME=script_name)
        self.assertEqual(logout.status_code, 302)
        self.assertEqual(logout["Location"], "/accounts/login/")
        self.assertEqual(external_location(logout["Location"]), "/proxy/5001/accounts/login/")
        after_logout = member.get("/", SCRIPT_NAME=script_name)
        self.assertEqual(after_logout.status_code, 302)
        self.assertEqual(after_logout["Location"], "/accounts/login/?next=/proxy/5001/")
        login_page = member.get("/accounts/login/", SCRIPT_NAME=script_name)
        self.assertEqual(login_page.status_code, 200)
        self.assertIn('action="/proxy/5001/accounts/login/"', login_page.content.decode())
        all_redirects = (chat_redirect, signup, login, profile_save, logout, after_logout)
        for response in all_redirects:
            self.assertNotIn("/proxy/5001/proxy/5001/", external_location(response["Location"]))
        all_pages = (signup_page, profile_page, billing_page, login_page, chat_page)
        for response in all_pages:
            self.assertNotIn("/proxy/5001/proxy/5001/", response.content.decode())

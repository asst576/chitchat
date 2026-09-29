from django.test import TestCase


class WorkspaceFoundationTests(TestCase):
    def test_home_page_renders_setup_notice(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "LiteChat")
        self.assertContains(response, "Chat features are pending")

    def test_health_check_returns_ok(self):
        response = self.client.get("/healthz/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

import shutil
import subprocess
import unittest

from django.conf import settings
from django.test import SimpleTestCase


class MarkdownRendererTests(SimpleTestCase):
    @unittest.skipUnless(shutil.which("node"), "Node.js is unavailable")
    def test_supported_markdown_and_untrusted_content_are_rendered_safely(self):
        script = settings.BASE_DIR / "chat" / "tests" / "markdown_renderer.test.cjs"
        renderer = (settings.BASE_DIR / "static" / "chat" / "markdown.js").read_text(encoding="utf-8")
        chat_client = (settings.BASE_DIR / "static" / "chat" / "chat.js").read_text(encoding="utf-8")
        result = subprocess.run(
            ["node", str(script)],
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertIn("Markdown parser/render safety checks passed.", result.stdout)
        self.assertIn('if (message.role === "assistant")', chat_client)
        self.assertIn("window.ChatMarkdown.render(message.content)", chat_client)
        self.assertIn("bubble.textContent = message.content", chat_client)
        self.assertIn("for (const message of messages) messageList.append(makeMessageRow(message));", chat_client)
        self.assertNotIn("innerHTML", renderer + chat_client)

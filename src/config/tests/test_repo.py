from pathlib import Path

from django.test import SimpleTestCase

REPO_ROOT = Path(__file__).resolve().parents[3]


class GitignoreTests(SimpleTestCase):
    def test_tailwind_binary_and_generated_css_are_ignored(self):
        lines = (REPO_ROOT / ".gitignore").read_text().splitlines()

        for entry in ("/src/assets/css/tailwind.css", "/src/.django_tailwind_cli/"):
            with self.subTest(entry=entry):
                self.assertIn(entry, lines)

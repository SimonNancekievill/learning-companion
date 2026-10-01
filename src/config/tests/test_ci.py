import re
from pathlib import Path

from django.test import SimpleTestCase

REPO_ROOT = Path(__file__).resolve().parents[3]


class DevRequirementsTests(SimpleTestCase):
    def test_pyyaml_is_pinned_to_an_exact_version(self):
        requirements = (REPO_ROOT / "requirements-dev.txt").read_text()

        self.assertRegex(requirements, re.compile(r"^PyYAML==\d+\.\d+\.\d+$", re.M))

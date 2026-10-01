import re
from pathlib import Path

import yaml
from django.test import SimpleTestCase

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_FILE = REPO_ROOT / ".github" / "workflows" / "ci.yml"


def workflow() -> dict:
    # YAML 1.1 parses the unquoted `on:` key as boolean True.
    return yaml.safe_load(WORKFLOW_FILE.read_text())


class DevRequirementsTests(SimpleTestCase):
    def test_pyyaml_is_pinned_to_an_exact_version(self):
        requirements = (REPO_ROOT / "requirements-dev.txt").read_text()

        self.assertRegex(requirements, re.compile(r"^PyYAML==\d+\.\d+\.\d+$", re.M))


class WorkflowFileTests(SimpleTestCase):
    def test_workflow_is_a_yaml_mapping_with_jobs(self):
        self.assertTrue(WORKFLOW_FILE.is_file(), f"{WORKFLOW_FILE} is missing")
        data = workflow()

        self.assertIsInstance(data, dict)
        self.assertIsInstance(data.get("jobs"), dict)

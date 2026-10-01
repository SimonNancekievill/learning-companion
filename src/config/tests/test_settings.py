import os
import re
import runpy
import shutil
import tempfile
from pathlib import Path
from unittest import mock

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

REPO_ROOT = Path(__file__).resolve().parents[3]
SETTINGS_FILE = REPO_ROOT / "src" / "config" / "settings.py"


def load_settings(env: dict[str, str], dotenv: str | None = None) -> dict:
    """Execute a copy of settings.py with exactly `env` as the process environment.

    The copy lives in a temporary repo tree, so `dotenv` (if given) becomes the
    repo-root `.env` it reads, and the developer's real `.env` is never seen.
    """
    with tempfile.TemporaryDirectory() as tmp:
        settings_copy = Path(tmp) / "src" / "config" / "settings.py"
        settings_copy.parent.mkdir(parents=True)
        shutil.copy(SETTINGS_FILE, settings_copy)
        if dotenv is not None:
            (Path(tmp) / ".env").write_text(dotenv)
        with mock.patch.dict(os.environ, env, clear=True):
            return runpy.run_path(str(settings_copy))


class RequirementsTests(SimpleTestCase):
    def test_django_environ_is_pinned_to_an_exact_version(self):
        requirements = (REPO_ROOT / "requirements.txt").read_text()

        self.assertRegex(requirements, re.compile(r"^django-environ==\d+\.\d+\.\d+$", re.M))


class SecretKeyTests(SimpleTestCase):
    def test_secret_key_is_read_from_dotenv_file(self):
        settings = load_settings({}, dotenv="DJANGO_SECRET_KEY=from-file\n")

        self.assertEqual(settings["SECRET_KEY"], "from-file")

    def test_secret_key_is_read_from_process_environment(self):
        settings = load_settings({"DJANGO_SECRET_KEY": "from-env"})

        self.assertEqual(settings["SECRET_KEY"], "from-env")

    def test_missing_secret_key_raises_improperly_configured(self):
        with self.assertRaises(ImproperlyConfigured):
            load_settings({}, dotenv="")

    def test_process_environment_takes_precedence_over_dotenv(self):
        settings = load_settings(
            {"DJANGO_SECRET_KEY": "from-env"}, dotenv="DJANGO_SECRET_KEY=from-file\n"
        )

        self.assertEqual(settings["SECRET_KEY"], "from-env")

    def test_settings_load_without_a_dotenv_file(self):
        settings = load_settings({"DJANGO_SECRET_KEY": "from-env"}, dotenv=None)

        self.assertEqual(settings["SECRET_KEY"], "from-env")

    def test_settings_source_contains_no_hardcoded_secret_key(self):
        self.assertNotIn("django-insecure-", SETTINGS_FILE.read_text())

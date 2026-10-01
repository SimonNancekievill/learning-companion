import os
import re
import runpy
import shutil
import tempfile
from pathlib import Path
from unittest import mock

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

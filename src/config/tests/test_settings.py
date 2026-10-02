import os
import re
import runpy
import shutil
import tempfile
from pathlib import Path
from unittest import mock

from django.conf import settings
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

    def test_django_tailwind_cli_and_its_dependencies_are_pinned_to_exact_versions(self):
        requirements = (REPO_ROOT / "requirements.txt").read_text()

        for package in ("django-tailwind-cli", "click", "django-click", "semver"):
            with self.subTest(package=package):
                pattern = re.compile(rf"^{re.escape(package)}==\d+\.\d+\.\d+$", re.M)

                self.assertRegex(requirements, pattern)


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


REQUIRED_ENV = {"DJANGO_SECRET_KEY": "test-key"}


class DebugTests(SimpleTestCase):
    def test_debug_follows_django_debug_and_defaults_to_false(self):
        cases = {"true": True, "1": True, "false": False, "0": False, None: False}
        for value, expected in cases.items():
            with self.subTest(DJANGO_DEBUG=value):
                env = REQUIRED_ENV | ({} if value is None else {"DJANGO_DEBUG": value})

                self.assertIs(load_settings(env)["DEBUG"], expected)


class AllowedHostsTests(SimpleTestCase):
    def test_allowed_hosts_is_comma_separated_list_and_defaults_to_empty(self):
        cases = {
            "localhost,127.0.0.1": ["localhost", "127.0.0.1"],
            "localhost, 127.0.0.1": ["localhost", "127.0.0.1"],
            None: [],
        }
        for value, expected in cases.items():
            with self.subTest(DJANGO_ALLOWED_HOSTS=value):
                env = REQUIRED_ENV | ({} if value is None else {"DJANGO_ALLOWED_HOSTS": value})

                self.assertEqual(load_settings(env)["ALLOWED_HOSTS"], expected)


class TailwindSettingsTests(SimpleTestCase):
    def test_django_tailwind_cli_is_installed(self):
        self.assertIn("django_tailwind_cli", settings.INSTALLED_APPS)

    def test_static_files_are_collected_from_the_assets_directory(self):
        self.assertEqual(settings.STATICFILES_DIRS, [settings.BASE_DIR / "assets"])

    def test_assets_directory_exists_in_a_fresh_checkout(self):
        self.assertTrue(Path(settings.STATICFILES_DIRS[0]).is_dir())

    def test_tailwind_version_is_pinned_to_an_exact_v4_release(self):
        self.assertRegex(settings.TAILWIND_CLI_VERSION, r"^4\.\d+\.\d+$")


class EnvExampleTests(SimpleTestCase):
    def setUp(self):
        self.text = (REPO_ROOT / ".env.example").read_text()
        self.lines = self.text.splitlines()

    def test_every_settings_variable_is_documented_with_a_comment(self):
        for name in ("DJANGO_SECRET_KEY", "DJANGO_DEBUG", "DJANGO_ALLOWED_HOSTS"):
            with self.subTest(name=name):
                index = next(i for i, line in enumerate(self.lines) if line.startswith(f"{name}="))

                self.assertTrue(self.lines[index - 1].startswith("#"))

    def test_openai_api_key_placeholder_is_kept(self):
        self.assertIn("OPENAI_API_KEY=", self.lines)

    def test_stale_not_read_note_is_removed(self):
        self.assertNotIn("not read by", self.text.lower())

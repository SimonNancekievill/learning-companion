from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.core.management import call_command
from django.test import TestCase

APP_DIR = Path(__file__).resolve().parent


class AccountsAppTests(TestCase):
    def test_accounts_app_is_registered_as_apps_accounts(self):
        self.assertEqual(apps.get_app_config("accounts").name, "apps.accounts")


class UserModelTests(TestCase):
    def test_active_user_model_is_accounts_user(self):
        self.assertEqual(settings.AUTH_USER_MODEL, "accounts.User")
        self.assertEqual(get_user_model()._meta.label, "accounts.User")

    def test_user_model_subclasses_abstract_user(self):
        self.assertTrue(issubclass(get_user_model(), AbstractUser))

    def test_user_model_migration_is_committed_and_up_to_date(self):
        self.assertTrue((APP_DIR / "migrations" / "0001_initial.py").is_file())

        call_command("makemigrations", "accounts", check=True, dry_run=True, verbosity=0)

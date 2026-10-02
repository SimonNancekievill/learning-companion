from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import AbstractUser
from django.core.management import call_command
from django.test import TestCase

from apps.accounts.forms import SignUpForm

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


class UserAdminTests(TestCase):
    def test_user_is_registered_in_admin_with_user_admin(self):
        user_model = get_user_model()

        self.assertTrue(admin.site.is_registered(user_model))
        self.assertIsInstance(admin.site.get_model_admin(user_model), UserAdmin)


class SignUpFormTests(TestCase):
    def test_sign_up_form_is_a_user_creation_form_for_the_custom_user(self):
        self.assertTrue(issubclass(SignUpForm, UserCreationForm))
        self.assertIs(SignUpForm._meta.model, get_user_model())
        self.assertEqual(list(SignUpForm().fields), ["username", "password1", "password2"])

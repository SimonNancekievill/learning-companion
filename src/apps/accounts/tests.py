from django.apps import apps
from django.test import TestCase


class AccountsAppTests(TestCase):
    def test_accounts_app_is_registered_as_apps_accounts(self):
        self.assertEqual(apps.get_app_config("accounts").name, "apps.accounts")

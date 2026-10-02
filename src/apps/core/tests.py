from django.apps import apps
from django.test import SimpleTestCase


class CoreAppTests(SimpleTestCase):
    def test_core_app_is_registered_as_apps_core(self):
        self.assertEqual(apps.get_app_config("core").name, "apps.core")

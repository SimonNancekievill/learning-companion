from django.apps import apps
from django.test import TestCase


class GoalsAppTests(TestCase):
    def test_goals_app_is_registered_as_apps_goals(self):
        self.assertEqual(apps.get_app_config("goals").name, "apps.goals")

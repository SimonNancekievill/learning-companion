from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import models
from django.test import TestCase


class GoalsAppTests(TestCase):
    def test_goals_app_is_registered_as_apps_goals(self):
        self.assertEqual(apps.get_app_config("goals").name, "apps.goals")


class GoalModelTests(TestCase):
    def goal_model(self):
        names = [m._meta.model_name for m in apps.get_app_config("goals").get_models()]
        self.assertIn("goal", names)
        return apps.get_model("goals", "Goal")

    def test_goal_belongs_to_its_owner_and_cascades(self):
        owner = self.goal_model()._meta.get_field("owner")

        self.assertIsInstance(owner, models.ForeignKey)
        self.assertIs(owner.related_model, get_user_model())
        self.assertEqual(owner.remote_field.related_name, "goals")
        self.assertIs(owner.remote_field.on_delete, models.CASCADE)

    def test_title_and_description_rules(self):
        meta = self.goal_model()._meta
        title, description = meta.get_field("title"), meta.get_field("description")

        self.assertEqual((title.max_length, title.blank), (200, False))
        self.assertIsInstance(description, models.TextField)
        self.assertTrue(description.blank)

    def test_status_choices_and_default(self):
        status = self.goal_model()._meta.get_field("status")

        self.assertEqual(
            status.choices,
            [("planned", "Planned"), ("in_progress", "In progress"), ("done", "Done")],
        )
        self.assertEqual(status.default, "planned")

    def test_timestamps_are_automatic(self):
        meta = self.goal_model()._meta

        self.assertTrue(meta.get_field("created_at").auto_now_add)
        self.assertTrue(meta.get_field("updated_at").auto_now)

    def test_goal_migration_is_up_to_date(self):
        self.goal_model()

        call_command("makemigrations", "goals", check=True, dry_run=True, verbosity=0)

    def test_str_is_the_title(self):
        self.assertEqual(str(self.goal_model()(title="Learn Django")), "Learn Django")

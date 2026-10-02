from datetime import UTC, datetime
from unittest import mock

from django.apps import apps
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import models
from django.test import TestCase

from apps.goals.models import Goal

T1, T2, T3 = (datetime(2026, 10, day, 9, 0, tzinfo=UTC) for day in (1, 2, 3))


def at(moment):
    """Freeze django.utils.timezone.now, which auto_now / auto_now_add read."""
    return mock.patch("django.utils.timezone.now", return_value=moment)


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


class GoalTimestampTests(TestCase):
    def test_created_at_is_set_once_and_updated_at_moves_on_save(self):
        owner = get_user_model().objects.create_user("ada", password="pw-12345-abc")
        with at(T1):
            goal = Goal.objects.create(owner=owner, title="Learn Django")
        created = (goal.created_at, goal.updated_at)

        with at(T2):
            goal.save()

        self.assertEqual(created, (T1, T1))
        self.assertEqual((goal.created_at, goal.updated_at), (T1, T2))


class GoalValidationTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user("ada", password="pw-12345-abc")

    def test_full_clean_rejects_bad_title_and_status(self):
        cases = {
            "empty title": ({"title": ""}, "title"),
            "title over 200 characters": ({"title": "x" * 201}, "title"),
            "unknown status": ({"title": "Learn Django", "status": "paused"}, "status"),
        }
        for case, (fields, field) in cases.items():
            with self.subTest(case=case):
                goal = Goal(owner=self.owner, **fields)

                with self.assertRaises(ValidationError) as raised:
                    goal.full_clean()
                self.assertIn(field, raised.exception.message_dict)

    def test_full_clean_accepts_an_empty_description(self):
        Goal(owner=self.owner, title="Learn Django", description="").full_clean()


class GoalOwnershipTests(TestCase):
    def test_deleting_a_user_deletes_only_their_goals(self):
        users = get_user_model().objects
        ada = users.create_user("ada", password="pw-12345-abc")
        bob = users.create_user("bob", password="pw-12345-abc")
        Goal.objects.create(owner=ada, title="Ada's goal")
        bobs = Goal.objects.create(owner=bob, title="Bob's goal")

        ada.delete()

        self.assertEqual(list(Goal.objects.all()), [bobs])

    def test_goals_are_ordered_most_recently_updated_first(self):
        ada = get_user_model().objects.create_user("ada", password="pw-12345-abc")
        with at(T1):
            first = Goal.objects.create(owner=ada, title="First")
        with at(T2):
            second = Goal.objects.create(owner=ada, title="Second")
        before = list(ada.goals.all())

        with at(T3):
            first.save()

        self.assertEqual(before, [second, first])
        self.assertEqual(list(ada.goals.all()), [first, second])


class GoalAdminTests(TestCase):
    def test_goal_admin_has_columns_filter_and_search(self):
        self.assertTrue(admin.site.is_registered(Goal))
        goal_admin = admin.site.get_model_admin(Goal)

        self.assertEqual(list(goal_admin.list_display), ["title", "owner", "status", "updated_at"])
        self.assertEqual(list(goal_admin.list_filter), ["status"])
        self.assertEqual(list(goal_admin.search_fields), ["title", "owner__username"])

    def test_superuser_can_search_goals_by_title(self):
        root = get_user_model().objects.create_superuser("root", password="pw-12345-abc")
        learn = Goal.objects.create(owner=root, title="Learn Django")
        Goal.objects.create(owner=root, title="Read SQL book")
        self.client.force_login(root)

        listing = self.client.get("/admin/goals/goal/")
        search = self.client.get("/admin/goals/goal/", {"q": "Django"})

        self.assertEqual(listing.status_code, 200)
        self.assertEqual(list(search.context["cl"].result_list), [learn])

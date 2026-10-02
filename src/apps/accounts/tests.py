import re
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import SESSION_KEY, get_user_model
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.views import LoginView
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import connection, models
from django.db.migrations.executor import MigrationExecutor
from django.shortcuts import resolve_url
from django.test import TestCase, TransactionTestCase
from django.urls import resolve, reverse
from django.utils.html import escape

from apps.accounts.forms import SignUpForm
from apps.accounts.models import Profile

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


SIGNUP_PATH = "/accounts/signup/"
LOGIN_PATH = "/accounts/login/"
LOGOUT_PATH = "/accounts/logout/"
STRONG_PASSWORD = "correct-horse-battery-staple"


def sign_up_data(username: str = "ada", password: str = STRONG_PASSWORD, confirm=None) -> dict:
    return {
        "username": username,
        "password1": password,
        "password2": password if confirm is None else confirm,
    }


class SignUpPageTests(TestCase):
    def test_anonymous_visitor_gets_sign_up_page(self):
        response = self.client.get(SIGNUP_PATH)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(reverse("accounts:signup"), SIGNUP_PATH)
        self.assertTemplateUsed(response, "accounts/signup.html")
        self.assertTemplateUsed(response, "base.html")
        self.assertIsInstance(response.context["form"], SignUpForm)

    def test_sign_up_page_has_csrf_token_and_title(self):
        response = self.client.get(SIGNUP_PATH)

        self.assertContains(response, "csrfmiddlewaretoken")
        self.assertContains(response, "<title>Sign up</title>")


class SignUpSubmitTests(TestCase):
    def test_valid_sign_up_creates_user_logs_them_in_and_redirects_home(self):
        response = self.client.post(SIGNUP_PATH, sign_up_data())

        self.assertRedirects(response, "/")
        user = get_user_model().objects.get()
        self.assertEqual(user.username, "ada")
        self.assertNotEqual(user.password, STRONG_PASSWORD)
        self.assertTrue(user.check_password(STRONG_PASSWORD))
        self.assertEqual(self.client.session.get(SESSION_KEY), str(user.pk))

    def test_invalid_sign_up_creates_no_user_and_re_renders_form_with_errors(self):
        get_user_model().objects.create_user("taken", password=STRONG_PASSWORD)
        cases = {
            "mismatched passwords": sign_up_data(confirm="something-else-entirely"),
            "password rejected by validators": sign_up_data(password="12345678"),
            "existing username in another case": sign_up_data(username="TAKEN"),
        }
        for case, data in cases.items():
            with self.subTest(case=case):
                response = self.client.post(SIGNUP_PATH, data)

                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, "accounts/signup.html")
                errors = response.context["form"].errors
                self.assertTrue(errors)
                for messages in errors.values():
                    for message in messages:
                        self.assertContains(response, escape(message))
                self.assertEqual(get_user_model().objects.count(), 1)
                self.assertIsNone(self.client.session.get(SESSION_KEY))


class SignUpWhenLoggedInTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("ada", password=STRONG_PASSWORD)
        self.client.force_login(self.user)

    def test_logged_in_user_is_redirected_home_on_get(self):
        response = self.client.get(SIGNUP_PATH)

        self.assertRedirects(response, "/")

    def test_logged_in_user_post_creates_no_user_and_keeps_session(self):
        response = self.client.post(SIGNUP_PATH, sign_up_data(username="grace"))

        self.assertRedirects(response, "/")
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertEqual(self.client.session.get(SESSION_KEY), str(self.user.pk))


class LoginPageTests(TestCase):
    def test_anonymous_visitor_gets_login_page_from_builtin_login_view(self):
        response = self.client.get(LOGIN_PATH)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(reverse("accounts:login"), LOGIN_PATH)
        self.assertIs(resolve(LOGIN_PATH).func.view_class, LoginView)
        self.assertTemplateUsed(response, "accounts/login.html")
        self.assertTemplateUsed(response, "base.html")
        self.assertIsInstance(response.context["form"], AuthenticationForm)

    def test_login_page_has_csrf_token_and_title(self):
        response = self.client.get(LOGIN_PATH)

        self.assertContains(response, "csrfmiddlewaretoken")
        self.assertContains(response, "<title>Log in</title>")


class LoginSubmitTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("ada", password=STRONG_PASSWORD)

    def test_valid_credentials_log_user_in_and_redirect_home(self):
        response = self.client.post(LOGIN_PATH, {"username": "ada", "password": STRONG_PASSWORD})

        self.assertRedirects(response, "/")
        self.assertEqual(self.client.session.get(SESSION_KEY), str(self.user.pk))

    def test_safe_next_is_followed_and_unsafe_next_is_ignored(self):
        credentials = {"username": "ada", "password": STRONG_PASSWORD}
        cases = {
            f"{LOGIN_PATH}?next={SIGNUP_PATH}": SIGNUP_PATH,
            f"{LOGIN_PATH}?next=https://evil.example/": "/",
        }
        for url, expected in cases.items():
            with self.subTest(url=url):
                response = self.client.post(url, credentials)

                self.assertRedirects(response, expected, fetch_redirect_response=False)
                self.client.logout()

    def test_wrong_credentials_log_nobody_in_and_show_error(self):
        response = self.client.post(LOGIN_PATH, {"username": "ada", "password": "wrong-password"})

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/login.html")
        errors = response.context["form"].non_field_errors()
        self.assertEqual(len(errors), 1)
        self.assertIn("Please enter a correct username and password", errors[0])
        self.assertContains(response, "Please enter a correct username and password")
        self.assertIsNone(self.client.session.get(SESSION_KEY))

    def test_logged_in_user_is_redirected_home_from_login_page(self):
        self.client.force_login(self.user)

        response = self.client.get(LOGIN_PATH)

        self.assertRedirects(response, "/")


class AuthSettingsTests(TestCase):
    def test_login_url_names_the_login_route(self):
        self.assertEqual(settings.LOGIN_URL, "accounts:login")
        self.assertEqual(resolve_url(settings.LOGIN_URL), LOGIN_PATH)

    def test_login_redirect_url_resolves_to_home(self):
        self.assertEqual(resolve_url(settings.LOGIN_REDIRECT_URL), "/")


class LogoutTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("ada", password=STRONG_PASSWORD)
        self.client.force_login(self.user)

    def test_post_logs_user_out_and_redirects_home(self):
        response = self.client.post(LOGOUT_PATH)

        self.assertRedirects(response, "/")
        self.assertEqual(reverse("accounts:logout"), LOGOUT_PATH)
        self.assertIsNone(self.client.session.get(SESSION_KEY))

    def test_get_is_refused_and_keeps_user_logged_in(self):
        response = self.client.get(LOGOUT_PATH)

        self.assertEqual(response.status_code, 405)
        self.assertEqual(self.client.session.get(SESSION_KEY), str(self.user.pk))

    def test_logout_redirect_url_resolves_to_home(self):
        self.assertIsNotNone(settings.LOGOUT_REDIRECT_URL)
        self.assertEqual(resolve_url(settings.LOGOUT_REDIRECT_URL), "/")


class NavTests(TestCase):
    def header(self, response) -> str:
        """Return the <header>...</header> of a response, failing if it is missing."""
        html = response.content.decode()
        self.assertIn("<header", html)
        self.assertIn("</header>", html)
        return html[html.index("<header") : html.index("</header>")]

    def test_anonymous_nav_shows_log_in_and_sign_up_links_only(self):
        header = self.header(self.client.get("/"))

        self.assertRegex(header, rf'<a\b[^>]*\bhref="{LOGIN_PATH}"[^>]*>\s*Log in\s*</a>')
        self.assertRegex(header, rf'<a\b[^>]*\bhref="{SIGNUP_PATH}"[^>]*>\s*Sign up\s*</a>')
        self.assertNotIn("Log out", header)
        self.assertNotIn(LOGOUT_PATH, header)

    def test_logged_in_nav_shows_username_and_post_log_out_form_only(self):
        user = get_user_model().objects.create_user("ada", password=STRONG_PASSWORD)
        self.client.force_login(user)

        header = self.header(self.client.get("/"))

        self.assertIn("ada", header)
        form = re.search(r"<form\b([^>]*)>(.*?)</form>", header, re.S)
        self.assertIsNotNone(form, "nav has no log-out form")
        attributes, body = form.groups()
        self.assertRegex(attributes, r'\bmethod="post"')
        self.assertRegex(attributes, rf'\baction="{LOGOUT_PATH}"')
        self.assertIn("csrfmiddlewaretoken", body)
        self.assertRegex(body, r"<button\b[^>]*>\s*Log out\s*</button>")
        self.assertNotIn(f'href="{LOGIN_PATH}"', header)
        self.assertNotIn(f'href="{SIGNUP_PATH}"', header)


class AuthPageCrossLinkTests(TestCase):
    def main(self, path: str) -> str:
        html = self.client.get(path).content.decode()
        self.assertIn("<main", html)
        return html[html.index("<main") : html.index("</main>")]

    def test_login_page_links_to_sign_up(self):
        main = self.main(LOGIN_PATH)

        self.assertIn("No account yet?", main)
        self.assertRegex(main, rf'<a\b[^>]*\bhref="{SIGNUP_PATH}"[^>]*>\s*Sign up\s*</a>')

    def test_sign_up_page_links_to_login(self):
        main = self.main(SIGNUP_PATH)

        self.assertIn("Already have an account?", main)
        self.assertRegex(main, rf'<a\b[^>]*\bhref="{LOGIN_PATH}"[^>]*>\s*Log in\s*</a>')


class AuthFlowTests(TestCase):
    def test_visitor_can_sign_up_log_out_and_log_back_in(self):
        self.client.post(SIGNUP_PATH, sign_up_data(username="grace"))
        user = get_user_model().objects.get(username="grace")
        self.assertEqual(self.client.session.get(SESSION_KEY), str(user.pk))

        self.client.post(LOGOUT_PATH)
        self.assertIsNone(self.client.session.get(SESSION_KEY))

        response = self.client.post(LOGIN_PATH, {"username": "grace", "password": STRONG_PASSWORD})

        self.assertRedirects(response, "/")
        self.assertEqual(self.client.session.get(SESSION_KEY), str(user.pk))


class ProfileModelTests(TestCase):
    def profile_model(self):
        names = [m._meta.model_name for m in apps.get_app_config("accounts").get_models()]
        self.assertIn("profile", names)
        return apps.get_model("accounts", "Profile")

    def test_profile_is_linked_one_to_one_to_the_user_and_cascades(self):
        user_field = self.profile_model()._meta.get_field("user")

        self.assertIsInstance(user_field, models.OneToOneField)
        self.assertIs(user_field.related_model, get_user_model())
        self.assertEqual(user_field.remote_field.related_name, "profile")
        self.assertIs(user_field.remote_field.on_delete, models.CASCADE)

    def test_profile_fields_may_be_blank_with_expected_limits(self):
        meta = self.profile_model()._meta
        name, cohort, focus_areas = (meta.get_field(f) for f in ("name", "cohort", "focus_areas"))

        self.assertEqual((name.max_length, name.blank), (100, True))
        self.assertEqual((cohort.max_length, cohort.blank), (50, True))
        self.assertIsInstance(focus_areas, models.JSONField)
        self.assertIs(focus_areas.default, list)
        self.assertTrue(focus_areas.blank)

    def test_profile_migration_is_up_to_date(self):
        self.profile_model()

        call_command("makemigrations", "accounts", check=True, dry_run=True, verbosity=0)

    def test_deleting_a_user_deletes_their_profile(self):
        profile_model = self.profile_model()
        user = get_user_model().objects.create_user("ada", password=STRONG_PASSWORD)
        profile_model.objects.get_or_create(user=user)

        user.delete()

        self.assertFalse(profile_model.objects.exists())

    def test_str_names_the_user(self):
        profile = self.profile_model()(user=get_user_model()(username="ada"))

        self.assertEqual(str(profile), "ada's profile")


class ProfileAutoCreateTests(TestCase):
    def assert_has_one_empty_profile(self, username: str):
        profiles = Profile.objects.filter(user__username=username)
        self.assertEqual(profiles.count(), 1)
        profile = profiles.get()
        self.assertEqual((profile.name, profile.cohort, profile.focus_areas), ("", "", []))

    def test_every_new_user_gets_exactly_one_empty_profile(self):
        users = get_user_model().objects
        creators = {
            "create_user": lambda: users.create_user("ada", password=STRONG_PASSWORD),
            "create_superuser": lambda: users.create_superuser("root", password=STRONG_PASSWORD),
            "sign-up": lambda: self.client.post(SIGNUP_PATH, sign_up_data(username="grace")),
        }
        usernames = {"create_user": "ada", "create_superuser": "root", "sign-up": "grace"}
        for path, create in creators.items():
            with self.subTest(path=path):
                create()

                self.assert_has_one_empty_profile(usernames[path])

    def test_saving_an_existing_user_again_creates_no_second_profile(self):
        user = get_user_model().objects.create_user("ada", password=STRONG_PASSWORD)
        user.first_name = "Ada"

        user.save()

        self.assert_has_one_empty_profile("ada")


BEFORE_BACKFILL = ("accounts", "0002_profile")
BACKFILL = ("accounts", "0003_backfill_profiles")


class ProfileBackfillMigrationTests(TransactionTestCase):
    def migrate(self, target) -> MigrationExecutor:
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(target)
        return executor

    def migrate_to_latest(self):
        executor = MigrationExecutor(connection)
        self.migrate(executor.loader.graph.leaf_nodes())

    def test_backfill_creates_missing_profiles_and_keeps_existing_ones(self):
        self.assertIn(BACKFILL, MigrationExecutor(connection).loader.graph.nodes)
        self.addCleanup(self.migrate_to_latest)
        old_apps = self.migrate([BEFORE_BACKFILL]).loader.project_state([BEFORE_BACKFILL]).apps
        OldUser = old_apps.get_model("accounts", "User")
        OldProfile = old_apps.get_model("accounts", "Profile")
        old = OldUser.objects.create(username="old")
        has = OldUser.objects.create(username="has")
        OldProfile.objects.create(user=has, name="Kept")

        new_apps = self.migrate([BACKFILL]).loader.project_state([BACKFILL]).apps

        NewProfile = new_apps.get_model("accounts", "Profile")
        backfilled = NewProfile.objects.get(user_id=old.pk)
        self.assertEqual((backfilled.name, backfilled.cohort, backfilled.focus_areas), ("", "", []))
        self.assertEqual(NewProfile.objects.filter(user_id=has.pk).count(), 1)
        self.assertEqual(NewProfile.objects.get(user_id=has.pk).name, "Kept")


class ProfileFocusAreasTests(TestCase):
    def setUp(self):
        self.profile = get_user_model().objects.create_user("ada", password=STRONG_PASSWORD).profile

    def test_full_clean_rejects_malformed_focus_areas(self):
        cases = {
            "not a list (str)": "django",
            "not a list (dict)": {"a": 1},
            "non-string item": ["ok", 3],
            "blank item": ["ok", "   "],
        }
        for case, value in cases.items():
            with self.subTest(case=case):
                self.profile.focus_areas = value

                with self.assertRaises(ValidationError) as raised:
                    self.profile.full_clean()
                self.assertIn("focus_areas", raised.exception.message_dict)

    def test_full_clean_trims_and_drops_case_insensitive_duplicates_in_order(self):
        cases = {
            "trim and dedupe": ([" Django ", "django", "SQL"], ["Django", "SQL"]),
            "already clean": (["SQL", "Django"], ["SQL", "Django"]),
        }
        for case, (value, expected) in cases.items():
            with self.subTest(case=case):
                self.profile.focus_areas = value

                self.profile.full_clean()

                self.assertEqual(self.profile.focus_areas, expected)

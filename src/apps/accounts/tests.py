from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import SESSION_KEY, get_user_model
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.views import LoginView
from django.core.management import call_command
from django.test import TestCase
from django.urls import resolve, reverse
from django.utils.html import escape

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


SIGNUP_PATH = "/accounts/signup/"
LOGIN_PATH = "/accounts/login/"
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

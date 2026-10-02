from django.apps import apps
from django.test import SimpleTestCase
from django.urls import reverse


class CoreAppTests(SimpleTestCase):
    def test_core_app_is_registered_as_apps_core(self):
        self.assertEqual(apps.get_app_config("core").name, "apps.core")


class HomePageTests(SimpleTestCase):
    def test_home_url_is_the_site_root(self):
        self.assertEqual(reverse("core:home"), "/")

    def test_anonymous_visitor_gets_home_page_rendered_on_base_layout(self):
        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/home.html")
        self.assertTemplateUsed(response, "base.html")

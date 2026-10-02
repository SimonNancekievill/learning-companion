from django.apps import apps
from django.template import engines
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

    def test_base_layout_loads_tailwind_stylesheet_in_head(self):
        response = self.client.get(reverse("core:home"))
        head = response.content.decode().split("</head>")[0]

        self.assertInHTML('<link rel="stylesheet" href="/static/css/tailwind.css">', head)


class BaseLayoutTests(SimpleTestCase):
    def render(self, blocks: str = "") -> str:
        """Render an inline template that extends base.html and overrides `blocks`."""
        return engines["django"].from_string('{% extends "base.html" %}' + blocks).render()

    def element(self, html: str, tag: str) -> str:
        """Return the first <tag>...</tag> element of `html`, failing if it is missing."""
        self.assertIn(f"<{tag}", html)
        self.assertIn(f"</{tag}>", html)
        return html[html.index(f"<{tag}") : html.index(f"</{tag}>") + len(f"</{tag}>")]

    def test_header_links_app_name_to_home(self):
        header = self.element(self.render(), "header")

        self.assertRegex(header, r'<a href="/"[^>]*>Learning Companion</a>')

    def test_nav_block_is_empty_by_default(self):
        header = self.element(self.render(), "header")

        self.assertRegex(header, r"<nav[^>]*></nav>")

    def test_nav_block_can_be_overridden_inside_header(self):
        html = self.render('{% block nav %}<a href="/x">X</a>{% endblock %}')
        header = self.element(html, "header")

        self.assertRegex(header, r'<nav[^>]*><a href="/x">X</a></nav>')

import re

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

    def test_home_page_shows_heading_and_app_description(self):
        content = self.client.get(reverse("core:home")).content.decode()
        main = content[content.index("<main") : content.index("</main>")]

        self.assertRegex(main, r"<h1[^>]*>\s*Learning Companion\s*</h1>")
        description = re.search(r"<p[^>]*>(.*?)</p>", main, re.S)
        self.assertIsNotNone(description, "home page has no description paragraph")
        for topic in ("goals", "sessions", "resources", "next steps"):
            with self.subTest(topic=topic):
                self.assertIn(topic, description.group(1))


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

    def test_nav_block_adds_nothing_by_default(self):
        self.assertEqual(self.render(), self.render("{% block nav %}{% endblock %}"))

    def test_nav_block_can_be_overridden_inside_header(self):
        html = self.render('{% block nav %}<a href="/x">X</a>{% endblock %}')
        header = self.element(html, "header")

        self.assertRegex(header, r'<nav[^>]*><a href="/x">X</a></nav>')

    def test_content_block_renders_inside_main(self):
        html = self.render("{% block content %}<p>Hello</p>{% endblock %}")
        main = self.element(html, "main")

        self.assertIn("<p>Hello</p>", main)

    def test_layout_has_a_footer(self):
        self.element(self.render(), "footer")

    def test_title_defaults_to_app_name(self):
        self.assertIn("<title>Learning Companion</title>", self.render())

    def test_title_block_can_be_overridden(self):
        html = self.render("{% block title %}Goals{% endblock %}")

        self.assertIn("<title>Goals</title>", html)

# Base layout and home page

## Story
As a visitor, I want a styled home page at `/` built on a shared base layout, so that every later page of the Learning Companion has a consistent look and a place for navigation.

## Acceptance criteria
- [x] AC1 `django-tailwind-cli` is listed in `requirements.txt` pinned to an exact version (`==`), and `django_tailwind_cli` is in `INSTALLED_APPS`.
- [x] AC2 A `core` app exists as `apps.core` (its `AppConfig.name` is `"apps.core"`) and is registered in `INSTALLED_APPS`.
- [x] AC3 `GET /` returns 200 for an anonymous user (no login required) and renders `core/home.html`, which extends `base.html`.
- [x] AC4 `base.html` lives in `src/templates/` (found via `TEMPLATES["DIRS"]`) and loads the Tailwind stylesheet (`{% tailwind_css %}` from django-tailwind-cli) in `<head>`.
- [x] AC5 `base.html` renders a `<header>` with the app name "Learning Companion" linking to `/`, and an overridable `nav` block inside the header (empty by default).
- [x] AC6 `base.html` renders a `<main>` element containing a `content` block, and a `<footer>`.
- [x] AC7 The home page shows the heading "Learning Companion" and a one-paragraph description of what the app does (tracking learning goals and sessions, attaching resources, AI summaries and next steps).
- [x] AC8 The page `<title>` is set through an overridable `title` block that defaults to "Learning Companion".
- [x] AC9 The CI workflow's `test` job runs `python src/manage.py tailwind build` before `manage.py test`, so a broken Tailwind build fails CI.
- [x] AC10 The downloaded Tailwind CLI binary and the generated CSS output are listed in `.gitignore`.

## Out of scope
- Navigation links (log in / sign up / log out) — ticket #5 fills the `nav` block.
- Any content that depends on the logged-in user (dashboard, goals).
- Docker build of Tailwind and `collectstatic` — ticket #23.
- Visual design beyond basic Tailwind utility classes; no custom theme or plugins.

## Notes
- Interview answers: ticket id `base-layout`; layout = header + content + footer with an empty `nav` block for #5; home page = static public intro; CI should run `tailwind build` now rather than defer it.
- Stack constraint from `CLAUDE.md`: django-tailwind-cli uses the standalone Tailwind binary, no Node.
- `CLAUDE.md` Commands should document the Tailwind dev/build commands once they exist.
- Existing `src/config/tests/test_ci.py` checks ci.yml with `assertIn` on run scripts; adding a build step must keep those tests green.

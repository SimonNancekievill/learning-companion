# Plan: base-layout

## Research summary
- **Project state:** `INSTALLED_APPS` has only the stock `django.contrib.*` apps. `TEMPLATES["DIRS"]` is `[]` with `APP_DIRS=True`. Static config is just `STATIC_URL = "static/"`. `src/config/urls.py` only routes `admin/`. `src/apps/` holds an empty `__init__.py`, and `src/templates/` does not exist. `BASE_DIR` is `src/`.
- **Conventions (CLAUDE.md):** create apps from `src/` with `../.venv/bin/python manage.py startapp core apps/core`, then set `AppConfig.name = "apps.core"`. App templates go in `src/apps/core/templates/core/`, shared ones in `src/templates/`. Runtime deps go in `requirements.txt` with `==` pins.
- **Tests:** existing tests are `SimpleTestCase` in `src/config/tests/`. They find the repo root with `REPO_ROOT = Path(__file__).resolve().parents[3]`. Each test is arrange/act, a blank line, then the asserts, and `subTest` is used for tables. Requirements are checked with a multiline regex. `ci.yml` is read with `yaml.safe_load` through `JobTestCase.job/steps/run_script(name)`, and step order uses `next(i for i, run in enumerate(runs) if ...)`. No test checks `.gitignore`. To run one module: `.venv/bin/python src/manage.py test config.tests.test_ci`. The full suite is `.venv/bin/python src/manage.py test src` (21 tests, green).
- **Ruff:** line length 100, py314, rules `E,F,W,I,B,UP,DJ`, double quotes.
- **django-tailwind-cli 4.8.1:** supports Django 6.1 / Python 3.14. Runtime deps are `click==8.5.0`, `django-click==2.5.0` and `semver==3.1.0`. Setup:
  - App name `django_tailwind_cli`. It requires a non-empty `STATICFILES_DIRS`.
  - Output defaults to `css/tailwind.css` under `STATICFILES_DIRS[0]`.
  - The binary and a managed `source.css` (`@import "tailwindcss";`) go in `BASE_DIR/.django_tailwind_cli/`, and the library writes a `.gitignore` there.
  - `TAILWIND_CLI_VERSION` defaults to `"latest"`, which is a network lookup with a fallback, so we pin it.
  - `{% load tailwind_cli %}{% tailwind_css %}` renders `<link rel="stylesheet" href="/static/css/tailwind.css">`. With the default `StaticFilesStorage` it doesn't need the built file to exist, so tests pass without a build.
  - `tailwind build` downloads the standalone binary on first run (no Node, so it works on ubuntu-latest). `tailwind runserver` runs runserver and watch together.

## Design decisions
- **`STATICFILES_DIRS = [BASE_DIR / "assets"]`**, so the generated CSS is `src/assets/css/tailwind.css`. This is the library's documented layout and keeps the managed source CSS out of the static dirs.
- **Use the library-managed `source.css`; no custom `TAILWIND_CLI_SRC_CSS`.** Tailwind v4's auto-scan finds the templates and we don't need a custom theme (out of scope).
- **Pin `TAILWIND_CLI_VERSION` to an exact Tailwind release.** The implementer uses the newest stable 4.x release listed on github.com/tailwindlabs/tailwindcss/releases on the day step 2 is done, and records the chosen version in that step's commit message. This keeps CI reproducible and avoids the GitHub API lookup on every build.
- **The home page is a function view in `apps/core/views.py` that renders `core/home.html`.** `apps/core/urls.py` (`app_name = "core"`, route name `home`) is included at `""` from `config/urls.py`. There's no login requirement because the page is public.
- **Block-level layout behaviour (nav/title/content overrides) is tested** by rendering an inline template string that extends `base.html`, via `django.template.engines["django"].from_string(...)`. That tests the layout contract without throwaway fixture templates.
- **CI:** a `Build Tailwind CSS` step (`python src/manage.py tailwind build`) goes in the `test` job after the secret-key step and before `Django tests`. Settings load at that point, so it needs `DJANGO_SECRET_KEY`.
- **`.gitignore`** gets `/src/assets/css/tailwind.css` and `/src/.django_tailwind_cli/`. The second is explicit even though the library self-ignores it, because AC10 asks for it.

## Steps
- [x] 1. `django-tailwind-cli` and its runtime deps are pinned in `requirements.txt` — test: `src/config/tests/test_settings.py` (extend `RequirementsTests`: `^django-tailwind-cli==\d+\.\d+\.\d+$` and the same for `click`, `django-click`, `semver`) — impl: `requirements.txt` (`django-tailwind-cli==4.8.1`, `click==8.5.0`, `django-click==2.5.0`, `semver==3.1.0`), then `.venv/bin/pip install -r requirements-dev.txt` — covers: AC1
- [x] 2. Tailwind is wired into settings — test: `src/config/tests/test_settings.py` (`django_tailwind_cli` in `settings.INSTALLED_APPS`; `settings.STATICFILES_DIRS == [settings.BASE_DIR / "assets"]`; `settings.TAILWIND_CLI_VERSION` matches `^4\.\d+\.\d+$`; `STATICFILES_DIRS[0]` is an existing directory) — impl: `src/config/settings.py`, `src/assets/.gitkeep` (amended during implementation: without a tracked placeholder, `src/assets/` is missing on a fresh clone and `staticfiles.W004` fires, since the generated CSS inside it is git-ignored) — covers: AC1
- [x] 3. The `core` app is registered as `apps.core` — test: `src/apps/core/tests.py` (`apps.get_app_config("core").name == "apps.core"`) — impl: `startapp core apps/core`, `src/apps/core/apps.py`, `INSTALLED_APPS` in `src/config/settings.py` — covers: AC2
- [x] 4. Anonymous `GET /` returns 200 and renders `core/home.html` extending `base.html` — test: `src/apps/core/tests.py` (client `get(reverse("core:home"))`, `assertEqual(status_code, 200)`, `assertTemplateUsed` for `core/home.html` and `base.html`; also check `reverse("core:home") == "/"`) — impl: `src/apps/core/views.py` (`home(request)`), `src/apps/core/urls.py`, `src/config/urls.py` (`include`), `src/apps/core/templates/core/home.html`, `src/templates/base.html` (minimal skeleton), `TEMPLATES["DIRS"] = [BASE_DIR / "templates"]` — covers: AC3, AC4 (location)
- [x] 5. `base.html` loads the Tailwind stylesheet in `<head>` — test: `src/apps/core/tests.py` (the home response's `<head>` section contains `<link rel="stylesheet" href="/static/css/tailwind.css">`) — impl: `src/templates/base.html` (`{% load tailwind_cli %}{% tailwind_css %}`) — covers: AC4
- [x] 6. The header shows "Learning Companion" linking to `/`, with an empty, overridable `nav` block — test: `src/apps/core/tests.py` (home response contains a `<header>` with `<a href="/">Learning Companion</a>`; an inline template extending `base.html` with `{% block nav %}<a href="/x">X</a>{% endblock %}` renders that link inside `<header>`; by default nothing renders between the nav markers) — impl: `src/templates/base.html` — covers: AC5
- [x] 7. The layout has `<main>` with a `content` block, and a `<footer>` — test: `src/apps/core/tests.py` (an inline template overriding `content` renders that text inside `<main>…</main>`; the rendered output contains `<footer`) — impl: `src/templates/base.html` — covers: AC6
- [ ] 8. `<title>` comes from an overridable `title` block that defaults to "Learning Companion" — test: `src/apps/core/tests.py` (default render contains `<title>Learning Companion</title>`; an inline template overriding `title` with "Goals" renders `<title>Goals</title>`) — impl: `src/templates/base.html` — covers: AC8
- [ ] 9. The home page shows the "Learning Companion" heading and a description of the app — test: `src/apps/core/tests.py` (response contains `<h1` … `Learning Companion`, and a `<p>` that mentions "goals", "sessions", "resources" and "next steps") — impl: `src/apps/core/templates/core/home.html` — covers: AC7
- [ ] 10. The CI test job builds Tailwind before running the tests — test: `src/config/tests/test_ci.py` (`TestJobTests`: `python src/manage.py tailwind build` is in `run_script("test")`, and its step index is after the secret-key step and before the `manage.py test` step) — impl: `.github/workflows/ci.yml` — covers: AC9
- [ ] 11. The Tailwind binary and generated CSS are git-ignored — test: new `src/config/tests/test_repo.py` (`SimpleTestCase` reading `REPO_ROOT / ".gitignore"` lines; asserts `/src/assets/css/tailwind.css` and `/src/.django_tailwind_cli/` are present) — impl: `.gitignore` — covers: AC10
- [ ] 12. Docs (no test, `docs(base-layout)` commit) — add the Tailwind commands to `CLAUDE.md` Commands: `.venv/bin/python src/manage.py tailwind runserver` (dev server with CSS watch) and `.venv/bin/python src/manage.py tailwind build`. Also note that the plain `runserver` still works but serves no CSS until a build has run.

## Coverage
| AC | Steps |
|----|-------|
| AC1 | 1, 2 |
| AC2 | 3 |
| AC3 | 4 |
| AC4 | 4, 5 |
| AC5 | 6 |
| AC6 | 7 |
| AC7 | 9 |
| AC8 | 8 |
| AC9 | 10 |
| AC10 | 11 |

## Risks
- Step 10: Tailwind v4 auto-scans from the working directory (the repo root in CI). It skips git-ignored paths such as `.venv/`, so the build should stay fast. If CI shows it scanning `.venv`, fix it in a new plan step, not ad hoc.
- Step 1 needs network access for `pip install`. Step 10's build needs network access in CI to download the binary, and GitHub-hosted runners have it.

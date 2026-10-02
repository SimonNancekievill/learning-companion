# Review: base-layout

## Verdict: PASS

No high-severity findings, every acceptance criterion is covered by a passing test, suite green (40 tests), `manage.py check` clean, `ruff check` and `ruff format --check` clean. The medium and low findings below are recorded as a follow-up backlog ticket ("Base layout hardening"), not fixed in this review.

## Acceptance criteria
- AC1 — covered by `config.tests.test_settings.RequirementsTests.test_django_tailwind_cli_and_its_dependencies_are_pinned_to_exact_versions`, `TailwindSettingsTests.test_django_tailwind_cli_is_installed` — PASS
- AC2 — covered by `apps.core.tests.CoreAppTests.test_core_app_is_registered_as_apps_core` — PASS
- AC3 — covered by `apps.core.tests.HomePageTests.test_home_url_is_the_site_root`, `test_anonymous_visitor_gets_home_page_rendered_on_base_layout` — PASS
- AC4 — covered by `HomePageTests.test_anonymous_visitor_gets_home_page_rendered_on_base_layout` (base.html used), `test_base_layout_loads_tailwind_stylesheet_in_head` — PASS (the `TEMPLATES["DIRS"]` location is only implied, see finding 3)
- AC5 — covered by `apps.core.tests.BaseLayoutTests.test_header_links_app_name_to_home`, `test_nav_block_is_empty_by_default`, `test_nav_block_can_be_overridden_inside_header` — PASS
- AC6 — covered by `BaseLayoutTests.test_content_block_renders_inside_main`, `test_layout_has_a_footer` — PASS
- AC7 — covered by `HomePageTests.test_home_page_shows_heading_and_app_description` — PASS
- AC8 — covered by `BaseLayoutTests.test_title_defaults_to_app_name`, `test_title_block_can_be_overridden` — PASS
- AC9 — covered by `config.tests.test_ci.TestJobTests.test_test_job_builds_tailwind_after_secret_key_and_before_tests` — PASS
- AC10 — covered by `config.tests.test_repo.GitignoreTests.test_tailwind_binary_and_generated_css_are_ignored` — PASS

## Findings
Code review (`code-reviewer`):
1. [medium] `src/config/tests/test_settings.py` (`test_assets_directory_exists_in_a_fresh_checkout`) — vacuous in CI and on any machine that has built Tailwind: the build creates `src/assets/css/`, so deleting `src/assets/.gitkeep` would go unnoticed. — Assert `(BASE_DIR / "assets" / ".gitkeep").is_file()` instead.
2. [low] `src/apps/core/tests.py:27` — `split("</head>")[0]` returns the whole document if `</head>` is missing, so the stylesheet test would pass with the link in `<body>`. — Extract `<head>` with the asserting `element()` helper.
3. [low] `src/apps/core/tests.py:21-23` — AC4's "found via `TEMPLATES["DIRS"]`" is not asserted directly. — Assert `get_template("base.html").origin.name == BASE_DIR / "templates" / "base.html"`.
4. [low] `src/apps/core/tests.py:33` — `content.index("<main")` errors (ValueError) instead of failing when `<main>` is missing. — Reuse `element()`.
5. [low] `src/apps/core/tests.py:57` — header-link regex depends on `href` preceding `class`. — Make the regex attribute-order independent.
6. [low] `.github/workflows/ci.yml:45-46` — the ~80 MB Tailwind binary is downloaded on every CI run. — Cache `src/.django_tailwind_cli/` keyed on `TAILWIND_CLI_VERSION` (optional).
7. [low] `CLAUDE.md:34` — the macOS `SSL_CERT_FILE` troubleshooting note was not in plan step 12. — Kept deliberately (useful, keeps TLS verification on); recorded here so artifacts match.
8. [low] `work/base-layout/plan.md` (Risks) — the note says Tailwind scans from the repo root; the library runs the binary with `cwd=BASE_DIR` (`src/`). Harmless; corrected understanding recorded here.

Security review (`security-reviewer`):
9. [medium] `.github/workflows/ci.yml:45-46`, `src/config/settings.py:130` — `tailwind build` downloads and executes the Tailwind binary with no checksum verification (the library only checks HTTPS and Content-Length), inside the job that holds `GITHUB_TOKEN` and the generated secret key. — Verify the pinned release against Tailwind's `sha256sums.txt` in a CI step and point `TAILWIND_CLI_PATH` at the verified binary with `TAILWIND_CLI_AUTOMATIC_DOWNLOAD = False` (or cache a verified binary).
10. [low] `.github/workflows/ci.yml:8-48` — no `permissions:` block and checkout persists credentials; more relevant now that a third-party binary runs in the job. — Already tracked by #29 (CI hardening).
11. [low] `requirements.txt` — new pins have no hashes (matches the existing repo pattern). — Optional: `pip-compile --generate-hashes` + `--require-hashes`.
12. [low, pre-existing] `.github/workflows/ci.yml` — actions pinned to tags, not SHAs. — Already tracked by #29.

Checked without issues: templates autoescape, no user data rendered, public home view intended, no secrets, binary dir not under `STATICFILES_DIRS`.

## Reviewed
commit 6ca5322, 2026-10-02

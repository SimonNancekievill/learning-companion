# Review: accounts-signup

## Verdict: PASS

No high or medium findings. Every acceptance criterion is covered by a passing test. The suite is green (52 tests), and `ruff check`, `ruff format --check`, `manage.py check` and `makemigrations --check --dry-run` are all clean. The low findings below are not fixed in this review. The auth-related ones are queued as the "Auth hardening" backlog ticket.

## Acceptance criteria
- AC1 — covered by `apps.accounts.tests.AccountsAppTests.test_accounts_app_is_registered_as_apps_accounts` — PASS
- AC2 — covered by `UserModelTests.test_active_user_model_is_accounts_user`, `test_user_model_subclasses_abstract_user`, `test_user_model_migration_is_committed_and_up_to_date` — PASS
- AC3 — covered by `UserAdminTests.test_user_is_registered_in_admin_with_user_admin` — PASS
- AC4 — covered by `SignUpPageTests.test_anonymous_visitor_gets_sign_up_page` — PASS
- AC5 — covered by `SignUpFormTests.test_sign_up_form_is_a_user_creation_form_for_the_custom_user` — PASS
- AC6 — covered by `SignUpSubmitTests.test_valid_sign_up_creates_user_logs_them_in_and_redirects_home` — PASS
- AC7 — covered by `SignUpSubmitTests.test_valid_sign_up_creates_user_logs_them_in_and_redirects_home` — PASS
- AC8 — covered by `SignUpSubmitTests.test_invalid_sign_up_creates_no_user_and_re_renders_form_with_errors` (characterization test, planned to pass on its first run) — PASS
- AC9 — covered by `SignUpPageTests.test_sign_up_page_has_csrf_token_and_title` — PASS
- AC10 — covered by `SignUpWhenLoggedInTests.test_logged_in_user_is_redirected_home_on_get`, `test_logged_in_user_post_creates_no_user_and_keeps_session` — PASS

## Findings
Code review (`code-reviewer`):
1. [low] `src/apps/accounts/tests.py:93-112` — the AC8 subtests assert only that some error exists, not that each case fails for its intended reason. — Add the expected error field per case (`password2`, `password2`, `username`) and assert that it is in `form.errors`.
2. [low] `src/apps/accounts/tests.py:20-51` — the non-DB test classes (app, model, admin, form) use `TestCase`, while `core` uses `SimpleTestCase` for non-DB tests. — Optional: switch them to `SimpleTestCase` for consistency and speed.
3. [low] `src/apps/accounts/views.py:21` — `login()` without `backend=` relies on there being exactly one authentication backend. — Nothing to do now. Pass `backend=` if a later ticket adds a backend.
4. [low] `src/apps/accounts/tests.py:34` — the migration test hard-codes `0001_initial.py`, which is brittle if migrations are squashed. The `makemigrations --check` call in the same test already covers the intent. — Acceptable as is.

Security review (`security-reviewer`):
5. [low, introduced here] `src/apps/accounts/urls.py:8` — sign-up has no rate limit, so accounts can be created in bulk, and the fake accounts could later spend OpenAI quota. — Add a per-IP throttle or CAPTCHA before the AI features ship (Auth hardening ticket).
6. [low, framework default] `src/apps/accounts/forms.py:6` — usernames can be enumerated through the "already exists" error (inherent to username sign-up, accepted), and Unicode homoglyph usernames are possible. Part of the reviewer's finding is incorrect: it said uniqueness was case-sensitive, but Django 6.1's `UserCreationForm.clean_username` already rejects case-insensitive duplicates via `username__iexact`, and AC8's "TAKEN" subtest proves it. — Optional: normalise or restrict the username character set (Auth hardening ticket).
7. [low, pre-existing] `src/config/settings.py` — `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS` and `SECURE_PROXY_SSL_HEADER` are not set. This matters more now that sessions carry authentication. — Configure them from env with secure defaults when `DEBUG=False`, and run `check --deploy` (Auth hardening ticket, or #23 Dockerfile).
8. [low, pre-existing] `src/config/urls.py:22` — the admin sits at the default `/admin/` and its login has no throttling. Sign-up cannot create staff users. — Optional: throttle the admin login (Auth hardening ticket).

The security reviewer checked these and found no issues: CSRF (middleware and `{% csrf_token %}`), session fixation (`login()` cycles the session key), password hashing and validators, mass assignment (only username/password1/password2 are bound, so `is_staff` etc. are ignored), open redirect (fixed `core:home` target, no `next`), XSS (autoescaped form and error rendering), and no secrets.

## Reviewed
commit 7941f77, 2026-10-02

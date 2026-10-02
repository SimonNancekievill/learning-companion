# Review: auth-login-logout

## Verdict: PASS

There are no high or medium findings, and every acceptance criterion is covered by a passing test. The suite is green (68 tests), and `ruff check`, `ruff format --check` and `manage.py check` are all clean. The two reworded base-layout tests (steps 1 and 8a) together still protect base-layout AC5, as confirmed by the code reviewer. All findings are low. The security ones are already tracked in #36 (Auth hardening). The test-quality ones are recorded here and not queued as a separate ticket.

## Acceptance criteria
- AC1 — covered by `apps.accounts.tests.LoginPageTests.test_anonymous_visitor_gets_login_page_from_builtin_login_view`, `test_login_page_has_csrf_token_and_title` — PASS
- AC2 — covered by `LoginSubmitTests.test_valid_credentials_log_user_in_and_redirect_home` — PASS
- AC3 — covered by `LoginSubmitTests.test_safe_next_is_followed_and_unsafe_next_is_ignored` (characterization) — PASS
- AC4 — covered by `LoginSubmitTests.test_wrong_credentials_log_nobody_in_and_show_error` (characterization) — PASS
- AC5 — covered by `LoginSubmitTests.test_logged_in_user_is_redirected_home_from_login_page` — PASS
- AC6 — covered by `AuthSettingsTests.test_login_url_names_the_login_route`, `test_login_redirect_url_resolves_to_home`, `LogoutTests.test_logout_redirect_url_resolves_to_home` — PASS
- AC7 — covered by `LogoutTests.test_post_logs_user_out_and_redirects_home`, `test_get_is_refused_and_keeps_user_logged_in` — PASS
- AC8 — covered by `NavTests.test_anonymous_nav_shows_log_in_and_sign_up_links_only` — PASS
- AC9 — covered by `NavTests.test_logged_in_nav_shows_username_and_post_log_out_form_only` — PASS
- AC10 — covered by `AuthPageCrossLinkTests.test_login_page_links_to_sign_up`, `test_sign_up_page_links_to_login` — PASS
- AC11 — covered by `AuthFlowTests.test_visitor_can_sign_up_log_out_and_log_back_in` (characterization) — PASS

## Findings
Code review (`code-reviewer`):
1. [low] `src/apps/core/tests.py:63` — no test enforces the design decision that the auth controls sit *outside* the `nav` block. Moving them into the block would keep every test green, yet a page that overrides `nav` would then lose the auth controls. — Add a test that renders a child template overriding `nav` and asserts that both the override and the auth controls appear in `<nav>`.
2. [low] `src/apps/accounts/tests.py:248` — `assertIn("ada", header)` is a weak substring check. — Anchor it as a text node (`>\s*ada\s*<`) and assert that it is not wrapped in a link.
3. [low] `src/apps/accounts/tests.py:174-178` — in the `next` subtest loop, `logout()` runs after the assertion, so a failing first case would leak a logged-in session into the second. — Log out at the start of each iteration. Optionally add a protocol-relative case such as `//evil.example/`.
4. [low] `src/apps/accounts/tests.py:268-271` — the `main()` helper does not assert `</main>`, so a missing closing tag raises `ValueError` instead of failing the test. — Assert both tags, like `header()` does.
5. [low] `src/apps/accounts/tests.py:198-200` — `settings.LOGIN_URL == "accounts:login"` restates the setting. This is kept deliberately as documentation of the "by URL name" design decision. `AuthSettingsTests` needs no database. — Optional: make it a `SimpleTestCase`.
6. [low] `src/apps/accounts/tests.py:216` — `reverse(...)` route checks are mixed into behaviour tests. This is cosmetic. — Optional: move them into their own test.
7. [low] `work/auth-login-logout/plan.md` — text mismatches:
   - The design decisions say "steps 4, 5 and 11" are characterization steps, but the steps and commits make it 4, 5 and 12.
   - The coverage table lists 8a under AC8, although 8a protects base-layout AC5.
   — Noted here as the authoritative record. The step list and commits are correct.

Security review (`security-reviewer`):
8. [low, accepted → #36] `src/apps/accounts/urls.py:10-16` — POST `/accounts/login/` has no throttling or lockout, so it is open to brute-force and credential stuffing. — Covered by #36 (Auth hardening).
9. [low, pre-existing → #36] `src/config/settings.py` — the secure cookie, HSTS and SSL-redirect settings are not set. This matters more now that sessions carry an authenticated user. — Covered by #36.
10. [low, forward-looking] `src/templates/base.html:15-20` — every page now renders the username, but only the auth views send `never_cache` headers, so a shared cache or the browser's back/forward cache could keep an authenticated page after logout. — Add `Cache-Control: private, no-store` for authenticated responses, either through middleware or `never_cache` on views that show user data, starting with the goals tickets (#9+).

The security reviewer checked and found no issues in:
- open redirect via `next` on login and logout (`url_has_allowed_host_and_scheme`)
- CSRF on login and on the POST-only logout
- session fixation (`cycle_key` on login, `flush` on logout)
- user enumeration on login (one generic error, plus hasher timing for unknown users)
- XSS (autoescaped username and form)
- clickjacking (`XFrameOptionsMiddleware`)

## Reviewed
commit 7ece0a8, 2026-10-02

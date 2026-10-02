# Plan: auth-login-logout

## Research summary
- **Project state (develop after accounts-signup):**
  - `apps/accounts/urls.py` has `app_name = "accounts"` and only `signup/`. `SignUpView` redirects authenticated users to `core:home`.
  - No `LOGIN_URL` / `LOGIN_REDIRECT_URL` / `LOGOUT_REDIRECT_URL` are set. Django's defaults are `/accounts/login/`, `/accounts/profile/` and `None`.
  - `base.html` `<header>` contains `<nav class="flex items-center gap-4 text-sm">{% block nav %}{% endblock %}</nav>`.
  - `signup.html` has a `title` block "Sign up", an `h1`, and a POST form with `{% csrf_token %}` and `{{ form }}`.
- **Existing tests touched by this ticket:**
  - `apps/core/tests.py` `BaseLayoutTests` renders `base.html` through `engines["django"].from_string(...).render()`, with no request and no `user`. It has helpers `render(blocks)` and `element(html, tag)`.
  - `test_nav_block_is_empty_by_default` asserts `<nav[^>]*></nav>`. Its premise was "empty until #5 fills it", and this ticket supersedes that (step 1).
  - `apps/accounts/tests.py` has `SIGNUP_PATH`, `STRONG_PASSWORD` and `sign_up_data()`, and imports `SESSION_KEY`.
- **Django 6.1.1 auth views (read from the installed source):**
  - `LoginView` defaults to `registration/login.html` and `redirect_authenticated_user=False`. When that flag is True, `dispatch` redirects to `get_success_url()`, and it guards against a redirect loop.
  - `next` is read from POST, then GET, and checked with `url_has_allowed_host_and_scheme` against the request host. An unsafe value becomes `""`, and the view falls back to `resolve_url(LOGIN_REDIRECT_URL)`.
  - `LogoutView.http_method_names = ["post", "options"]`, so GET returns 405. After logout it redirects to `resolve_url(LOGOUT_REDIRECT_URL)`.
  - `AuthenticationForm` raises a non-field error: "Please enter a correct %(username)s and password. Note that both fields may be case-sensitive."
  - `LOGIN_URL` and the redirect settings go through `resolve_url`, so URL names such as `"accounts:login"` work.
- **Conventions:** `TestCase` for request/DB tests, `SimpleTestCase` for template-only ones. Arrange/act, a blank line, then the asserts. Ruff line length 100. One module runs with `.venv/bin/python src/manage.py test apps.accounts`.

## Design decisions
- **Views:** use the built-in `django.contrib.auth.views.LoginView` and `LogoutView`, configured in `apps/accounts/urls.py`. No subclasses are needed:
  - `LoginView.as_view(template_name="accounts/login.html", redirect_authenticated_user=True)`
  - `LogoutView.as_view()`
- **Settings:** `LOGIN_URL = "accounts:login"`, `LOGIN_REDIRECT_URL = "core:home"` and `LOGOUT_REDIRECT_URL = "core:home"`. URL names avoid duplicating paths.
- **Auth controls live in `base.html`, inside `<nav>` but *after* `{% block nav %}{% endblock %}`, not inside the block.** Pages can then add their own nav links without dropping the auth controls. The `nav` block itself stays empty by default.
  - Anonymous: "Log in" → `accounts:login` and "Sign up" → `accounts:signup`.
  - Authenticated: `{{ user.get_username }}` as plain text, plus `<form method="post" action="{% url 'accounts:logout' %}">{% csrf_token %}<button type="submit">Log out</button></form>`.
  - The template only uses `user`, from the auth context processor. Inline renders without a request see an anonymous (undefined) user, so they show the logged-out links.
- **Step 1 deliberately rewrites one base-layout test, as its own green step.** `test_nav_block_is_empty_by_default` becomes `test_nav_block_adds_nothing_by_default`. It asserts that rendering with no override equals rendering with an empty `nav` override, so the *block* stays empty while the `<nav>` element gains auth controls. The test is reworded to its lasting intent, not deleted.
- **Characterization steps:** Django's `LoginView` already provides safe-`next` handling (AC3) and the invalid-login error (AC4). The end-to-end flow (AC11) also works once all the pieces exist. So steps 4, 5 and 11 are test-only steps expected to pass on their first run, committed as `test(auth-login-logout): ...`. If one fails, it is fixed minimally in that step and committed as `feat(...)`.

## Steps
- [x] 1. Reword the base-layout nav test to its lasting intent (test-only, green before and after, `test(...)` commit) — test: `src/apps/core/tests.py` (replace `test_nav_block_is_empty_by_default` with `test_nav_block_adds_nothing_by_default`: `self.render() == self.render("{% block nav %}{% endblock %}")`) — impl: none — covers: groundwork for AC8/AC9 (keeps base-layout AC5 tested)
- [x] 2. Anonymous `GET /accounts/login/` renders the login page — test: `src/apps/accounts/tests.py` (`LoginPageTests`: status 200; `reverse("accounts:login") == "/accounts/login/"`; templates `accounts/login.html` and `base.html`; `response.context["form"]` is an `AuthenticationForm`; body contains `csrfmiddlewaretoken` and `<title>Log in</title>`; `resolve(LOGIN_PATH).func.view_class is LoginView`) — impl: `src/apps/accounts/urls.py` (`login/`), `src/apps/accounts/templates/accounts/login.html` — covers: AC1
- [x] 3. Valid credentials log the user in and redirect to `/` — test: `src/apps/accounts/tests.py` (`LoginSubmitTests`: create a user, POST username + password → `assertRedirects(response, "/")`, `session.get(SESSION_KEY) == str(user.pk)`). It's red because the default `LOGIN_REDIRECT_URL` is `/accounts/profile/` — impl: `LOGIN_REDIRECT_URL = "core:home"` in `src/config/settings.py` — covers: AC2, AC6 (part)
- [x] 4. A safe `next` is followed and an unsafe one is ignored (characterization, `test(...)` commit) — test: `src/apps/accounts/tests.py` (POST to `/accounts/login/?next=/accounts/signup/` → `assertRedirects(..., "/accounts/signup/", fetch_redirect_response=False)`; POST with `?next=https://evil.example/` → redirect to `/`) — impl: none expected — covers: AC3
- [ ] 5. Wrong credentials log nobody in and show the error (characterization, `test(...)` commit) — test: `src/apps/accounts/tests.py` (wrong password → status 200, `accounts/login.html` used, `form.non_field_errors()` contains the `invalid_login` message, body contains "Please enter a correct username and password", `session.get(SESSION_KEY)` is `None`) — impl: none expected — covers: AC4
- [ ] 6. A logged-in user is redirected away from the login page — test: `src/apps/accounts/tests.py` (`force_login`, then GET `/accounts/login/` → `assertRedirects(..., "/")`) — impl: `redirect_authenticated_user=True` in `src/apps/accounts/urls.py` — covers: AC5
- [ ] 7. `LOGIN_URL` names the login route — test: `src/apps/accounts/tests.py` (`AuthSettingsTests`: `settings.LOGIN_URL == "accounts:login"` and `resolve_url(settings.LOGIN_URL) == "/accounts/login/"`; `resolve_url(settings.LOGIN_REDIRECT_URL) == "/"`) — impl: `LOGIN_URL = "accounts:login"` in `src/config/settings.py` — covers: AC6
- [ ] 8. POST logout logs out and redirects home, and GET is refused — test: `src/apps/accounts/tests.py` (`LogoutTests`: `reverse("accounts:logout") == "/accounts/logout/"`; logged in, POST → `assertRedirects(..., "/")` and `session.get(SESSION_KEY)` is `None`; logged in, GET → 405 and the session still holds the user; `resolve_url(settings.LOGOUT_REDIRECT_URL) == "/"`) — impl: `src/apps/accounts/urls.py` (`logout/`, `LogoutView`), `LOGOUT_REDIRECT_URL = "core:home"` — covers: AC7, AC6
- [ ] 9. Anonymous nav shows "Log in" and "Sign up" and no log-out control — test: `src/apps/accounts/tests.py` (`NavTests`, `TestCase`: GET `/`, cut out `<header>…</header>`; regex links `<a\b[^>]*href="/accounts/login/"[^>]*>\s*Log in\s*</a>` and `href="/accounts/signup/"` … `Sign up`; `"Log out"` and `/accounts/logout/` not in the header) — impl: `src/templates/base.html` — covers: AC8
- [ ] 10. Logged-in nav shows the username and a POST log-out form with CSRF, and no login/sign-up links — test: `src/apps/accounts/tests.py` (`NavTests`: `force_login(user "ada")`, GET `/`, cut out the header; contains `ada`; a `<form` with `method="post"` and `action="/accounts/logout/"` containing `csrfmiddlewaretoken` and a `<button` … `Log out`; `href="/accounts/login/"` and `href="/accounts/signup/"` absent) — impl: `src/templates/base.html` — covers: AC9
- [ ] 11. The login and sign-up pages link to each other — test: `src/apps/accounts/tests.py` (the `<main>` of the login page contains a link to `/accounts/signup/` with text "Sign up" and the copy "No account yet?"; the `<main>` of the sign-up page contains a link to `/accounts/login/` with text "Log in" and the copy "Already have an account?") — impl: `accounts/login.html`, `accounts/signup.html` — covers: AC10
- [ ] 12. Sign up → log out → log in works end-to-end (characterization, `test(...)` commit) — test: `src/apps/accounts/tests.py` (`AuthFlowTests`: POST sign-up → logged in; POST logout → `SESSION_KEY` gone; POST login with the same credentials → redirect `/`, session holds the same user pk) — impl: none expected — covers: AC11

## Coverage
| AC | Steps |
|----|-------|
| AC1 | 2 |
| AC2 | 3 |
| AC3 | 4 |
| AC4 | 5 |
| AC5 | 6 |
| AC6 | 3, 7, 8 |
| AC7 | 8 |
| AC8 | 9 |
| AC9 | 10 |
| AC10 | 11 |
| AC11 | 12 |

## Risks
- Steps 9 and 10 assert on the rendered header of the home page. Link checks use attribute-order-independent regexes, which avoids the brittleness flagged in the base-layout review.
- Steps 4, 5 and 12 are expected to be green on their first run. That is intentional and recorded here. It is not a skipped red.

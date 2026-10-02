# Plan: accounts-signup

## Research summary
- **Project state (develop after base-layout):**
  - `INSTALLED_APPS` has the contrib apps, `django_tailwind_cli` and `apps.core`.
  - `AUTH_USER_MODEL`, `LOGIN_URL`, `LOGIN_REDIRECT_URL` and `AUTHENTICATION_BACKENDS` are not set (defaults apply: ModelBackend only), and the 4 standard password validators are configured.
  - `src/config/urls.py` routes `admin/` and `""` → `apps.core.urls` (`core:home` = `/`).
  - `base.html` has `title`, `nav` and `content` blocks. No app has migrations yet.
- **Conventions:**
  - Create the app from `src/` with `../.venv/bin/python manage.py startapp accounts apps/accounts` and set `AppConfig.name = "apps.accounts"`.
  - Templates go in `src/apps/accounts/templates/accounts/`.
  - Existing tests are `SimpleTestCase` with arrange/act, a blank line, then the asserts. This ticket needs the DB, so it uses `django.test.TestCase`.
  - Ruff: line length 100, rules `E,F,W,I,B,UP,DJ`.
  - To run one module: `.venv/bin/python src/manage.py test apps.accounts`.
- **Django 6.1.1 auth internals (read from the installed source):**
  - `UserCreationForm` inherits `Meta.model = auth.User` (hard-coded import). A custom user needs `class Meta(UserCreationForm.Meta): model = User`. Its case-insensitive duplicate check uses `self._meta.model`, so it follows the custom model.
  - The form's fields are `username`, `password1` and `password2`, with password validators run in `_post_clean`. `usable_password` exists only on `AdminUserCreationForm`.
  - `admin.site.register(User, UserAdmin)` works for a bare `AbstractUser` subclass.
  - `login(request, user)` needs no `backend=` when there is exactly one authentication backend.
  - `CreateView.form_valid` sets `self.object = form.save()` and then redirects to `get_success_url()`.
  - `redirect_authenticated_user` exists only on `LoginView`. A sign-up view has to do the same check in `dispatch`.
- **Local DB:** `src/db.sqlite3` (git-ignored) already has every default migration applied, including `admin.0001` against `auth.User`. Switching `AUTH_USER_MODEL` makes `migrate` fail there with `InconsistentMigrationHistory`. Tests are unaffected because they build a fresh test database.

## Design decisions
- **The custom user model is `apps/accounts/models.py: class User(AbstractUser)` with no extra fields**, and `AUTH_USER_MODEL = "accounts.User"`. Introducing it before any other app has migrations is the cheap, recommended point.
- **The form is `apps/accounts/forms.py: class SignUpForm(UserCreationForm)`** with `Meta(UserCreationForm.Meta): model = User`. It reuses Django's validation and hashing.
- **The view is `apps/accounts/views.py: class SignUpView(CreateView)`:**
  - `form_class = SignUpForm`, `template_name = "accounts/signup.html"`, `success_url = reverse_lazy("core:home")`.
  - `form_valid` calls `super()` and then `login(self.request, self.object)`.
  - `dispatch` redirects authenticated users to `core:home` before any form handling.
  - It's a class-based view because the generic edit view already gives the invalid-form re-render for free.
- **URLs:** `apps/accounts/urls.py` with `app_name = "accounts"` and `path("signup/", ..., name="signup")`, included at `accounts/` from `config/urls.py`. #5's built-in auth views can then sit beside it under `/accounts/`.
- **Admin:** `admin.site.register(User, UserAdmin)` with the stock `UserAdmin`, since there are no extra fields to show.
- **Characterization step:** with `CreateView`, the invalid-POST behaviour (AC8) works as soon as the valid path exists. Step 7 is therefore a test-only step that is expected to pass on its first run. It's committed as `test(accounts-signup): ...` and recorded as such instead of faking a red. Every other step starts red.

## Steps
- [x] 1. The `accounts` app is registered as `apps.accounts` — test: `src/apps/accounts/tests.py` (`apps.get_app_config("accounts").name == "apps.accounts"`) — impl: `startapp accounts apps/accounts`, `src/apps/accounts/apps.py`, `INSTALLED_APPS`; remove unused scaffold (`views.py`) until it is needed — covers: AC1
- [ ] 2. `accounts.User` is the active user model and its migration is committed — test: `src/apps/accounts/tests.py` (`get_user_model()` is `apps.accounts.models.User`, a subclass of `AbstractUser`; `settings.AUTH_USER_MODEL == "accounts.User"`; `call_command("makemigrations", "accounts", check=True, dry_run=True)` raises no `SystemExit`; `apps/accounts/migrations/0001_initial.py` exists) — impl: `src/apps/accounts/models.py`, `AUTH_USER_MODEL` in `src/config/settings.py`, `makemigrations accounts` → `src/apps/accounts/migrations/0001_initial.py` — covers: AC2. **After this step the local `src/db.sqlite3` must be deleted and re-migrated (see Risks).**
- [ ] 3. The custom `User` is registered in the admin with `UserAdmin` — test: `src/apps/accounts/tests.py` (`admin.site.is_registered(User)` and `isinstance(admin.site._registry[User], UserAdmin)`) — impl: `src/apps/accounts/admin.py` — covers: AC3
- [ ] 4. `SignUpForm` is a `UserCreationForm` bound to `accounts.User` with exactly username / password1 / password2 — test: `src/apps/accounts/tests.py` (`issubclass(SignUpForm, UserCreationForm)`, `SignUpForm._meta.model is User`, `list(SignUpForm().fields) == ["username", "password1", "password2"]`) — impl: `src/apps/accounts/forms.py` — covers: AC5
- [ ] 5. Anonymous `GET /accounts/signup/` renders the sign-up page — test: `src/apps/accounts/tests.py` (`reverse("accounts:signup") == "/accounts/signup/"`; status 200; `assertTemplateUsed` `accounts/signup.html` and `base.html`; `response.context["form"]` is a `SignUpForm`; the body contains `csrfmiddlewaretoken`; the body contains `<title>Sign up</title>`) — impl: `src/apps/accounts/views.py` (`SignUpView`, a `CreateView` with `success_url` → `core:home`), `src/apps/accounts/urls.py`, `include("apps.accounts.urls")` at `accounts/` in `src/config/urls.py`, `src/apps/accounts/templates/accounts/signup.html` (`title` block, `<form method="post">` with `{% csrf_token %}`, `{{ form }}`, submit button) — covers: AC4, AC9
- [ ] 6. A valid POST creates one user with a hashed password, logs them in and redirects to `/` — test: `src/apps/accounts/tests.py` (POST username + matching strong passwords → `assertRedirects(response, "/")`; `User.objects.count() == 1`; `user.check_password(raw)` is true and `user.password != raw`; `int(self.client.session["_auth_user_id"]) == user.pk`). It's red because `CreateView` alone saves but does not log in — impl: `SignUpView.form_valid` calls `login()` — covers: AC6, AC7
- [ ] 7. Invalid POSTs create no user and re-render the form with errors (characterization, expected green on the first run, `test(...)` commit) — test: `src/apps/accounts/tests.py` (`subTest` table: mismatched passwords, a password rejected by the validators (e.g. `"12345678"`), and an existing username in a different case → status 200, `accounts/signup.html` used, `response.context["form"].errors` non-empty, the error text is in the body, and the user count is unchanged) — impl: none expected. If any case fails, fix it minimally in this step and commit as `feat(...)` instead — covers: AC8
- [ ] 8. A logged-in user is redirected away from the sign-up page — test: `src/apps/accounts/tests.py` (`force_login` an existing user; GET → `assertRedirects(..., "/")`; POST valid new credentials → redirect to `/`, user count unchanged, `session["_auth_user_id"]` is still the original user) — impl: `SignUpView.dispatch` — covers: AC10

## Coverage
| AC | Steps |
|----|-------|
| AC1 | 1 |
| AC2 | 2 |
| AC3 | 3 |
| AC4 | 5 |
| AC5 | 4 |
| AC6 | 6 |
| AC7 | 6 |
| AC8 | 7 |
| AC9 | 5 |
| AC10 | 8 |

## Risks
- **Local database reset (step 2):** the existing `src/db.sqlite3` has `admin.0001_initial` applied against `auth.User`, so `migrate` will raise `InconsistentMigrationHistory` once `AUTH_USER_MODEL` changes. The fix is to delete `src/db.sqlite3` and run `migrate` again. The file is git-ignored and the project has no real data yet, but any local superuser is lost. The implementer asks the user before deleting it. Tests and CI are unaffected.
- **`_auth_user_id` session key:** this is Django's documented session key (`django.contrib.auth.SESSION_KEY`). Tests import `SESSION_KEY` instead of hard-coding the string.

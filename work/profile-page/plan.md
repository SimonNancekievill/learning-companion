# Plan: profile-page

## Research summary
- **Project state (develop after user-profile):**
  - `Profile` lives in `apps/accounts/models.py`. Its `clean()` maps `None` to `[]`, rejects non-lists and non-string or blank items, then trims and dedupes case-insensitively.
  - It has no size caps yet.
  - `apps/accounts/urls.py` has `signup/`, `login/` and `logout/`. `LOGIN_URL = "accounts:login"`.
  - `django.contrib.messages` is fully wired (app, middleware, context processor), but `base.html` renders no messages yet.
  - The nav shows `<span class="text-slate-600">{{ user.get_username }}</span>` when logged in. The existing `NavTests` assert only `"ada" in header`, the logout form, and the absence of login/signup links, so turning the span into a link breaks nothing.
- **Django 6.1.1 internals (read from the installed source):**
  - **ModelForm field override.** A ModelForm field named like a model field (`focus_areas = forms.CharField`) replaces the generated field. `construct_instance` then assigns whatever `clean_focus_areas()` returns (a list) via `save_form_data`.
  - **Initial value.** Initial data comes from `model_to_dict`, so it is the raw list. Join it into `"Django, SQL"` in `__init__` (`self.initial["focus_areas"] = ", ".join(...)`).
  - **Model validation.** `_post_clean` runs `instance.full_clean(exclude=...)`, where fields that already have form errors are excluded. A `ValidationError({"focus_areas": ...})` from `Model.clean()` attaches to that form field, with no `ValueError` because the field is on the form.
  - **`LoginRequiredMixin`.** It redirects to `resolve_url(LOGIN_URL)?next=<path>`.
  - **`SuccessMessageMixin`.** It goes before `UpdateView` and sends `messages.success(success_message % cleaned_data)` after `super().form_valid()`.
  - **`UpdateView`.** `get_object()` can be overridden to return the request user's profile, and `success_url = reverse_lazy(...)` works.
- **Conventions:** `TestCase` for DB and request tests. Arrange/act, a blank line, then the asserts. Ruff line length 100. Tests go in `src/apps/accounts/tests.py`, which already has `LOGIN_PATH`, `STRONG_PASSWORD`, the `NavTests.header()` helper and `Profile` imported.

## Design decisions
- **View:** `ProfileView(LoginRequiredMixin, SuccessMessageMixin, UpdateView)` in `apps/accounts/views.py`:
  - `form_class = ProfileForm` and `template_name = "accounts/profile.html"`.
  - `success_url = reverse_lazy("accounts:profile")` and `success_message = "Profile saved."`.
  - `get_object()` returns `Profile.objects.get_or_create(user=self.request.user)[0]`.

  The route is `path("profile/", ..., name="profile")`, with no URL parameters, so there is no way to address another user's profile.
- **Form:** `ProfileForm(ModelForm)` in `apps/accounts/forms.py`:
  - `Meta.fields = ["name", "cohort", "focus_areas"]`, explicit, and never `user`.
  - `focus_areas = forms.CharField(required=False, help_text="Comma-separated, e.g. Django, SQL")`.
  - `clean_focus_areas()` splits on commas and drops pieces that are blank after `strip()`. It does *not* trim or dedupe, because the model's `clean()` already does that.
  - `__init__` joins the instance's list into comma-separated initial text.
- **Caps live in `Profile.clean()`, after normalisation:** more than 10 tags, or a tag longer than 30 characters, raises a `ValidationError` on `focus_areas`. The admin inline and the page then share one rule.
- **Messages:** `base.html` renders `{% if messages %}` as a list at the top of `<main>`, above the `content` block, for every page.
- **Nav:** the username becomes `<a href="{% url 'accounts:profile' %}">{{ user.get_username }}</a>`.
- **Characterization steps:** once the view uses an explicit-fields ModelForm, rejecting a smuggled `user` field (AC3 POST part / AC5), the view-level cap error (AC7 page part) and the other invalid input (AC8) all work with no new code. Steps 7, 9 and 10 are therefore test-only steps expected to pass on their first run, committed as `test(profile-page): ...`. If one fails, it is fixed minimally in that step and committed as `feat(...)`.

## Steps
- [x] 1. `Profile.full_clean()` caps focus areas at 10 tags of at most 30 characters — test: `src/apps/accounts/tests.py` (`ProfileFocusAreasTests`):
  - rejected with a `"focus_areas"` error: 11 distinct tags, and one tag of 31 characters
  - accepted: exactly 10 tags of 30 characters, and 11 entries that dedupe to 10, e.g. 10 tags plus a case-duplicate

  impl: `Profile.clean()` in `src/apps/accounts/models.py` — covers: AC7 (model)
- [ ] 2. `ProfileForm` edits exactly name, cohort and focus areas, as comma-separated text — test: `src/apps/accounts/tests.py` (`ProfileFormTests`):
  - `hasattr(apps.accounts.forms, "ProfileForm")` is asserted first, so the red is a failure, not an `ImportError`
  - `list(ProfileForm().fields) == ["name", "cohort", "focus_areas"]`
  - an instance with `["Django", "SQL"]` gives `form.initial["focus_areas"] == "Django, SQL"`
  - a bound form with `focus_areas="Django, , sql, SQL ,"` is valid, and `save()` stores `["Django", "sql"]`

  impl: `ProfileForm` in `src/apps/accounts/forms.py` — covers: AC3 (form), AC4 (parsing)
- [ ] 3. A logged-in user sees their own pre-filled profile page — test: `src/apps/accounts/tests.py` (`ProfilePageTests`):
  - logged in as `ada`, with a profile of name "Ada", cohort "B1" and `["Django", "SQL"]`
  - `GET /accounts/profile/` → 200 with templates `accounts/profile.html` and `base.html`
  - `reverse("accounts:profile") == "/accounts/profile/"` and `resolve(...).kwargs == {}`
  - the body has `csrfmiddlewaretoken`, `<title>Profile</title>`, and `value="Ada"`, `value="B1"`, `value="Django, SQL"`

  impl: `ProfileView` (an `UpdateView` with `get_object` → `request.user.profile`), the `profile/` URL, and `src/apps/accounts/templates/accounts/profile.html` — covers: AC2
- [ ] 4. Anonymous visitors are sent to login — test: `src/apps/accounts/tests.py` (`GET /accounts/profile/` anonymously → `assertRedirects(..., "/accounts/login/?next=/accounts/profile/")`) — impl: `LoginRequiredMixin` on `ProfileView` — covers: AC1
- [ ] 5. A valid POST saves the requesting user's profile and redirects back — test: `src/apps/accounts/tests.py`:
  - POST name / cohort / `"Django, , sql, SQL ,"` → `assertRedirects(..., "/accounts/profile/")`
  - after `refresh_from_db()` the profile has the new name and cohort and `["Django", "sql"]`

  impl: `success_url = reverse_lazy("accounts:profile")` — covers: AC4
- [ ] 6. "Profile saved." is shown once, through a messages area in `base.html` — test: `src/apps/accounts/tests.py`:
  - a valid POST with `follow=True` → the body contains "Profile saved." exactly once
  - a second plain GET does not contain it
  - an inline template that extends `base.html`, rendered with `{"messages": ["Hello there"]}`, contains "Hello there"

  impl: `SuccessMessageMixin` + `success_message` on `ProfileView`, and a `{% if messages %}` list in `src/templates/base.html` — covers: AC4 (message), AC10
- [ ] 7. Only the requesting user's profile is read or written, and a smuggled `user` field is ignored (characterization, `test(...)` commit) — test: `src/apps/accounts/tests.py`:
  - users `ada` and `bob`; bob's profile has name "Bobby Secret" and cohort "Z9"
  - ada POSTs valid data plus `user=<bob.pk>`
  - afterwards ada's profile still belongs to ada and has the new values
  - bob's profile is unchanged (`refresh_from_db`)
  - ada's GET page contains neither "Bobby Secret" nor "Z9"

  impl: none expected — covers: AC3 (POST), AC5
- [ ] 8. A logged-in user without a profile gets one on first visit — test: `src/apps/accounts/tests.py`:
  - delete ada's profile (re-fetch the user so the cached relation is gone), then `force_login`
  - `GET /accounts/profile/` → 200, and exactly one profile now exists for ada, with empty defaults

  It's red because `request.user.profile` raises `RelatedObjectDoesNotExist`. impl: `get_object` uses `Profile.objects.get_or_create(user=self.request.user)[0]` — covers: AC6
- [ ] 9. Posting too many or too long tags shows the error and saves nothing (characterization, `test(...)` commit) — test: `src/apps/accounts/tests.py`:
  - subtests: 11 comma-separated tags, and one 31-character tag
  - each gives status 200, template `accounts/profile.html`, `"focus_areas"` in `form.errors`, the error text in the body, and the profile unchanged after `refresh_from_db()`

  impl: none expected — covers: AC7 (page)
- [ ] 10. Other invalid input re-renders with the error and changes nothing (characterization, `test(...)` commit) — test: `src/apps/accounts/tests.py` (POST `name="x" * 101` → 200, `"name"` in `form.errors`, the profile unchanged) — impl: none expected — covers: AC8
- [ ] 11. The username in the nav links to the profile page — test: `src/apps/accounts/tests.py` (`NavTests`: logged in as ada, the header matches `<a\b[^>]*\bhref="/accounts/profile/"[^>]*>\s*ada\s*</a>`; the anonymous header contains no `href="/accounts/profile/"`) — impl: `src/templates/base.html` — covers: AC9

## Coverage
| AC | Steps |
|----|-------|
| AC1 | 4 |
| AC2 | 3 |
| AC3 | 2, 7 |
| AC4 | 2, 5, 6 |
| AC5 | 7 |
| AC6 | 8 |
| AC7 | 1, 9 |
| AC8 | 10 |
| AC9 | 11 |
| AC10 | 6 |

## Risks
- **Step 4's red will be an exception, not an assertion failure.** Without `LoginRequiredMixin`, an anonymous request hits `request.user.profile` on an `AnonymousUser` and raises `AttributeError`. That is the real failure mode of the missing behaviour, like the `IntegrityError` reds in #6, and is accepted as such.
- **Step 8's red has the same shape:** `RelatedObjectDoesNotExist`, which is the defect itself.
- **Steps 7, 9 and 10 are expected to be green on their first run.** That is deliberate and recorded here. They are not skipped reds.
- **Tailwind:** the messages area and the profile form use new utility classes. Run `tailwind build` before checking the page in the browser. CI builds it anyway.

# Plan: goal-model

## Research summary
- **Project state (develop after profile-page):**
  - `INSTALLED_APPS` ends with `apps.core` and `apps.accounts`.
  - `AUTH_USER_MODEL = "accounts.User"`, `USE_TZ = True` and `TIME_ZONE = "UTC"`.
  - There is no `goals` app yet.
- **Conventions:**
  - Create the app from `src/` with `../.venv/bin/python manage.py startapp goals apps/goals` and set `AppConfig.name = "apps.goals"`. Remove unused scaffold, as was done for `accounts` (its `views.py` stays out until #9).
  - Tests go in `src/apps/goals/tests.py` and use `TestCase`, with arrange/act, a blank line, then the asserts.
  - App registration is tested with `apps.get_app_config(label).name`.
  - Model metadata is tested through a helper that first asserts the model name is in `apps.get_app_config(...).get_models()`. The red is then a failure, not a `LookupError`. After that, `apps.get_model(...)._meta.get_field(...)`.
  - The migration check is `call_command("makemigrations", "<app>", check=True, dry_run=True, verbosity=0)`.
  - Ruff: line length 100, `DJ` rules. DJ008 wants a `__str__` on every model, so `__str__` goes in the model step to keep every commit lint-clean.
- **Django 6.1.1 internals:**
  - `DateTimeField.pre_save` sets the value with `timezone.now()` from `django.utils`, looked up at call time. So `mock.patch("django.utils.timezone.now", return_value=...)` makes `created_at`/`updated_at` deterministic.
  - `QuerySet.update()` bypasses `auto_now`.
  - Admin search uses `?q=`, and `search_fields = ["title", "owner__username"]` becomes `icontains` lookups. The changelist context has `cl.result_list`.

## Design decisions
- **The `Goal` model** lives in `apps/goals/models.py`:
  - `owner = ForeignKey(settings.AUTH_USER_MODEL, on_delete=CASCADE, related_name="goals")`
  - `title = CharField(max_length=200)`
  - `description = TextField(blank=True)`
  - `status = CharField(max_length=20, choices=Status.choices, default=Status.PLANNED)`
  - `created_at = DateTimeField(auto_now_add=True)` and `updated_at = DateTimeField(auto_now=True)`
  - `Meta.ordering = ["-updated_at"]` and `__str__` returns `title`.
- **`Goal.Status(models.TextChoices)`** is nested in `Goal`: `PLANNED = "planned", "Planned"`, `IN_PROGRESS = "in_progress", "In progress"`, `DONE = "done", "Done"`. #11 will reuse the values.
- **Timestamp tests patch `django.utils.timezone.now`** with fixed times instead of sleeping. Fast SQLite tests can otherwise produce equal timestamps and make ordering flaky.
- **Admin:** `@admin.register(Goal) class GoalAdmin` with:
  - `list_display = ["title", "owner", "status", "updated_at"]`
  - `list_filter = ["status"]`
  - `search_fields = ["title", "owner__username"]`
- **Characterization steps:** once the fields from step 2 exist, Django's field machinery already provides three behaviours with no new code: the `auto_now`/`auto_now_add` timestamps (AC3), `full_clean()` validation of blank title, length and choices (AC4), and the cascade on user delete (AC5). Steps 3, 4 and 5 are therefore test-only steps expected to pass on their first run, committed as `test(goal-model): ...`. If one fails, it is fixed minimally in that step and committed as `feat(...)`.

## Steps
- [ ] 1. The `goals` app is registered as `apps.goals` — test: `src/apps/goals/tests.py` (`apps.get_app_config("goals").name == "apps.goals"`) — impl: `startapp goals apps/goals` (remove the unused `views.py`, `admin.py` and `models.py` scaffold for now), `src/apps/goals/apps.py`, `INSTALLED_APPS` — covers: AC1
- [ ] 2. The `Goal` model has the agreed fields, choices, default and `__str__`, and its migration is committed — test: `src/apps/goals/tests.py` (`GoalModelTests`):
  - `"goal"` is among the app's models
  - `owner` is a `ForeignKey` to `AUTH_USER_MODEL` with `related_name == "goals"` and `on_delete is CASCADE`
  - `title` has max length 200 and `blank` False
  - `description` is a `TextField` with `blank` True
  - `status` has `choices == [("planned", "Planned"), ("in_progress", "In progress"), ("done", "Done")]` and default `"planned"`
  - `created_at.auto_now_add` and `updated_at.auto_now` are set
  - `makemigrations goals --check --dry-run` passes
  - `str(Goal(title="Learn Django")) == "Learn Django"`

  impl: `src/apps/goals/models.py`, `makemigrations goals` → `0001_initial.py` — covers: AC2, AC7
- [ ] 3. Timestamps are set on create, and only `updated_at` moves on save (characterization, `test(...)` commit) — test: `src/apps/goals/tests.py` (patch `django.utils.timezone.now` to T1 for create, then to T2 for a re-save; assert `created_at == T1` both times, and `updated_at` is T1 then T2) — impl: none expected — covers: AC3
- [ ] 4. `full_clean()` rejects bad titles and statuses and accepts an empty description (characterization, `test(...)` commit) — test: `src/apps/goals/tests.py` (subtests: `title=""`, `title="x"*201` and `status="paused"` each raise `ValidationError` with the field key in `message_dict`; a goal with `description=""` and a valid title passes) — impl: none expected — covers: AC4
- [ ] 5. Deleting a user deletes only their goals (characterization, `test(...)` commit) — test: `src/apps/goals/tests.py` (goals for `ada` and `bob`; deleting `ada` leaves exactly bob's goal) — impl: none expected — covers: AC5
- [ ] 6. A user's goals are ordered by most recently updated first — test: `src/apps/goals/tests.py`:
  - create "First" at T1 and "Second" at T2 → `list(user.goals.all()) == [Second, First]`
  - re-save "First" at T3 → `[First, Second]`

  It's red without `Meta.ordering`: SQLite returns pk order, so the first assertion sees `[First, Second]`. — impl: `Meta.ordering = ["-updated_at"]` — covers: AC6
- [ ] 7. `Goal` is in the admin with list columns, a status filter and search — test: `src/apps/goals/tests.py` (`GoalAdminTests`):
  - the registered model admin has the planned `list_display`, `list_filter` and `search_fields`
  - as a superuser, `GET /admin/goals/goal/` returns 200
  - `GET /admin/goals/goal/?q=Django` with goals "Learn Django" and "Read SQL book" gives `cl.result_list == ["Learn Django"]`

  impl: `src/apps/goals/admin.py` — covers: AC8

## Coverage
| AC | Steps |
|----|-------|
| AC1 | 1 |
| AC2 | 2 |
| AC3 | 3 |
| AC4 | 4 |
| AC5 | 5 |
| AC6 | 6 |
| AC7 | 2 |
| AC8 | 7 |

## Risks
- **Steps 3, 4 and 5 are expected to be green on their first run.** That is deliberate and recorded here. They are not skipped reds.
- **Local DB:** run `migrate` after step 2. The change is additive, so no reset is needed.
- **Step 6: the first assertion catches a missing ordering.** With insertion and pk order First→Second, `[Second, First]` is only produced by `-updated_at`. The re-save assertion then shows that `updated_at`, not `created_at`, drives the order.

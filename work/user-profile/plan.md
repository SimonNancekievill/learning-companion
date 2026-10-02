# Plan: user-profile

## Research summary
- **Project state:**
  - `apps/accounts/models.py` has only `class User(AbstractUser): pass`. Migrations are `0001_initial.py` only.
  - `apps/accounts/apps.py` (`AccountsConfig`, `name = "apps.accounts"`) has no `ready()`. There is no signals precedent anywhere in `src/`.
  - `apps/accounts/admin.py` does `admin.site.register(User, UserAdmin)`, and the existing `UserAdminTests` asserts the registered admin `isinstance(..., UserAdmin)`. A subclass keeps that test green.
  - `apps/accounts/tests.py` defines the constants `SIGNUP_PATH`, `LOGIN_PATH`, `LOGOUT_PATH`, `STRONG_PASSWORD` and the helper `sign_up_data()`, plus 14 test classes.
- **Django 6.1.1 internals (read from the installed source):**
  - `Model.full_clean()` runs `clean_fields()`, then `clean()` (always, even after field errors), then `validate_unique()`, then `validate_constraints()`. A `ValidationError({"focus_areas": ...})` raised from `clean()` is attached to that field.
  - `clean_fields()` *skips* a `blank=True` field whose value is in `EMPTY_VALUES` (`[]`, `{}`, `""`, `None`).
  - `JSONField.validate` only checks that the value serialises to JSON, so a str or dict passes. The list/item checks therefore belong in `Profile.clean()`, which always runs.
  - Data migrations can be tested with `MigrationExecutor(connection)`: `.loader.build_graph()`, `.migrate([(app, name)])` and `.loader.project_state((app, name)).apps` to get the historical models.
  - Admin: `StackedInline` takes `model`, `can_delete` and `fk_name`. `UserAdmin.inlines` can be set on a subclass. Since `User` is our own model and is registered only in `accounts/admin.py`, it is enough to change the `register` call; `unregister` is not needed.
- **Conventions:** `TestCase` for DB tests. Arrange/act, a blank line, then the asserts. Ruff line length 100, with `migrations/` excluded from ruff. One module runs with `.venv/bin/python src/manage.py test apps.accounts`.

## Design decisions
- **Model:** `Profile` in `apps/accounts/models.py` with these fields:
  - `user = OneToOneField(settings.AUTH_USER_MODEL, on_delete=CASCADE, related_name="profile")`
  - `name = CharField(max_length=100, blank=True)`
  - `cohort = CharField(max_length=50, blank=True)`
  - `focus_areas = JSONField(default=list, blank=True)`

  It sits next to the `User` it extends.
- **Validation and normalisation live in `Profile.clean()`, not in field validators.** `clean_fields()` skips empty values and `JSONField` accepts any JSON, so `clean()` is the one hook that always sees the value:
  - It raises `ValidationError({"focus_areas": ...})` if the value is not a list, or if any item is not a string or is blank after `strip()`.
  - Otherwise it rewrites `self.focus_areas`: items are trimmed, case-insensitive duplicates are dropped, and the first occurrence and the order are kept.
- **Auto-creation:**
  - `apps/accounts/signals.py` defines a `post_save` receiver for the `User` model that does `Profile.objects.create(user=instance)` only when `created` is true.
  - The receiver is connected by importing the signals module in `AccountsConfig.ready()`.
  - This covers `create_user`, `create_superuser`, admin and sign-up alike, and a re-save is a no-op.
- **Backfill:**
  - Schema migration `0002_profile` comes from `makemigrations`.
  - Data migration `0003_backfill_profiles` comes from `makemigrations --empty accounts --name backfill_profiles`. It uses historical models via `apps.get_model` and creates a `Profile` for every user without one. Its reverse is `migrations.RunPython.noop`.
  - Historical models don't fire our receiver, so the test can create "pre-existing" profile-less users at `0002`.
- **Migration test:** `TransactionTestCase` with `MigrationExecutor`. It migrates `accounts` back to `0002_profile`, arranges the data with historical models, migrates forward to `0003_backfill_profiles` and asserts the result. `tearDown` migrates back to the latest leaf nodes. `TransactionTestCase` is used because SQLite schema changes can't run inside the `TestCase` transaction.
- **Admin:**
  - `ProfileInline(admin.StackedInline)` with `model = Profile` and `can_delete = False`.
  - `class UserAdmin(BaseUserAdmin)` with `inlines = [ProfileInline]`, registered for `User`. `Profile` itself is not registered.

## Steps
- [x] 1. `Profile` model with its schema migration, one-to-one and cascading — test: `src/apps/accounts/tests.py` (`ProfileModelTests`):
  - `"profile"` is among the `accounts` app's model names (assertion first, so red is a failure, not a `LookupError`)
  - via `apps.get_model("accounts", "Profile")`: `user` is a `OneToOneField` to `AUTH_USER_MODEL` with `related_name == "profile"` and `on_delete is CASCADE`
  - `name` has max 100 and is blank-able; `cohort` has max 50 and is blank-able; `focus_areas` is a `JSONField` with default `list` and is blank-able
  - `makemigrations accounts --check --dry-run` passes
  - deleting a user whose profile was created manually removes the profile

  impl: `src/apps/accounts/models.py`, `makemigrations accounts` → `0002_profile.py` — covers: AC1, AC4
- [x] 2. `str(profile)` names its user — test: `src/apps/accounts/tests.py` (`str(Profile(user=User(username="ada"))) == "ada's profile"`) — impl: `Profile.__str__` — covers: AC8
- [x] 3. Every new user gets exactly one empty profile automatically — test: `src/apps/accounts/tests.py` (`ProfileAutoCreateTests`):
  - subtests for `create_user`, `create_superuser` and a POST to `SIGNUP_PATH`: each leaves exactly one `Profile` for that user, with `name == ""`, `cohort == ""` and `focus_areas == []`
  - re-saving the user (`user.first_name = "Ada"; user.save()`) leaves the count at 1 and raises nothing

  impl: `src/apps/accounts/signals.py`, `AccountsConfig.ready()` in `src/apps/accounts/apps.py` — covers: AC2, AC3
- [x] 4. A data migration backfills profiles for existing users — test: `src/apps/accounts/tests.py` (`ProfileBackfillMigrationTests(TransactionTestCase)`):
  - assertion first that `("accounts", "0003_backfill_profiles")` is in `executor.loader.graph.nodes`
  - migrate to `0002_profile`
  - with historical models, create user `"old"` without a profile and user `"has"` with a profile `name="Kept"`
  - migrate to `0003_backfill_profiles`
  - `"old"` now has exactly one profile with empty defaults, and `"has"` still has exactly one profile, still named `"Kept"`
  - `tearDown` migrates back to the leaf nodes

  impl: `makemigrations accounts --empty --name backfill_profiles` → `src/apps/accounts/migrations/0003_backfill_profiles.py` (a `RunPython` forward function, `noop` reverse) — covers: AC5
- [x] 5. `full_clean()` rejects malformed `focus_areas` — test: `src/apps/accounts/tests.py` (`ProfileFocusAreasTests`, subtests over `"django"`, `{"a": 1}`, `["ok", 3]`, `["ok", "   "]` → `ValidationError` whose `message_dict` has the key `"focus_areas"`) — impl: `Profile.clean()` (validation part) — covers: AC6
- [x] 6. `full_clean()` trims tags and drops case-insensitive duplicates in order — test: `src/apps/accounts/tests.py` (`[" Django ", "django", "SQL"]` → `["Django", "SQL"]` after `full_clean()`; `["SQL", "Django"]` stays as it is) — impl: `Profile.clean()` (normalisation part) — covers: AC7
- [ ] 7. The profile is edited inline on the User admin page — test: `src/apps/accounts/tests.py` (`UserAdminTests` additions):
  - the registered admin for `User` has an inline whose `model` is `Profile`
  - `admin.site.is_registered(Profile)` is false
  - as a superuser (created via `create_superuser`, which triggers the signal), `GET /admin/accounts/user/<pk>/change/` returns 200 and contains `name="profile-0-name"`, `name="profile-0-cohort"` and `name="profile-0-focus_areas"`

  impl: `src/apps/accounts/admin.py` (`ProfileInline`, `UserAdmin(BaseUserAdmin)` subclass) — covers: AC9

## Coverage
| AC | Steps |
|----|-------|
| AC1 | 1 |
| AC2 | 3 |
| AC3 | 3 |
| AC4 | 1 |
| AC5 | 4 |
| AC6 | 5 |
| AC7 | 6 |
| AC8 | 2 |
| AC9 | 7 |

## Risks
- **Migration test cost and isolation (step 4):** `TransactionTestCase` flushes tables after the test, and migrating backwards and forwards takes a moment. `tearDown` must always restore the leaf nodes, even if the test fails (via `addCleanup`), or later tests would run against an old schema.
- **Local DB:** after steps 1 and 4, run `migrate` on the local `src/db.sqlite3`. This is additive, so no reset is needed this time.
- **Step 3 changes how existing tests create users:** every `create_user` now also creates a profile. No existing test counts profiles, so nothing should break. If one does, it gets fixed as its own step, not silently.

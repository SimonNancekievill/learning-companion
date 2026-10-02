# Review: goal-model

## Verdict: PASS

No high or medium findings, and every acceptance criterion is covered by a passing test. The suite is green (112 tests, also with `--shuffle`). `ruff check`, `ruff format --check`, `manage.py check` and `makemigrations --check` are all clean, and the working tree was verified clean after both reviewers ran.

All findings are low and are not fixed here. The ones that matter for the goal pages are carried into #9 and #10 as requirements, listed at the end.

## Acceptance criteria
- AC1 — covered by `apps.goals.tests.GoalsAppTests.test_goals_app_is_registered_as_apps_goals` — PASS
- AC2 — covered by `GoalModelTests.test_goal_belongs_to_its_owner_and_cascades`, `test_title_and_description_rules`, `test_status_choices_and_default`, `test_timestamps_are_automatic`, `test_goal_migration_is_up_to_date` — PASS
- AC3 — covered by `GoalTimestampTests.test_created_at_is_set_once_and_updated_at_moves_on_save` (characterization) — PASS
- AC4 — covered by `GoalValidationTests.test_full_clean_rejects_bad_title_and_status`, `test_full_clean_accepts_an_empty_description` (characterization) — PASS
- AC5 — covered by `GoalOwnershipTests.test_deleting_a_user_deletes_only_their_goals` (characterization) — PASS
- AC6 — covered by `GoalOwnershipTests.test_goals_are_ordered_most_recently_updated_first` — PASS
- AC7 — covered by `GoalModelTests.test_str_is_the_title` — PASS
- AC8 — covered by `GoalAdminTests.test_goal_admin_has_columns_filter_and_search`, `test_superuser_can_search_goals_by_title` — PASS

## Findings
Code review (`code-reviewer`). These checks came out sound:
- **Timestamp patching:** it is scoped to `create()`/`save()` only, and the UTC-aware datetimes are correct under `USE_TZ`.
- **Ordering test:** its red is genuine (SQLite pk order).
- **Conventions:** `TextChoices` nested in the model and the `Meta` placement follow Django and ruff conventions.

Findings:
1. [low] `src/apps/goals/tests.py:120` — the ordering test sits in `GoalOwnershipTests`, which is about cascade deletes. — Move it into its own `GoalOrderingTests` class.
2. [low] `src/apps/goals/tests.py:73-83` — the timestamp test asserts on the in-memory instance only. — Use `refresh_from_db()` so the test proves the values were persisted.
3. [low] `src/apps/goals/tests.py:144-155` — the admin behaviour test covers title search only. `owner__username` search and the status filter are only checked by restating the config. — Optionally add `q=<username>` and `?status=done` changelist cases.
4. [low] `src/apps/goals/tests.py:132-141` — the config-restating admin test is acceptable as planned, see 3.
5. [low] `src/apps/goals/migrations/0002_goal_ordering.py` — an options-only migration on a never-released app. Squashing it into `0001` before merge would be tidier. — Kept as is: it is harmless, `0001` is already applied locally, and rewriting it would need a local `migrate goals zero`. Not worth a FAIL round-trip.
6. [info] `src/apps/goals/models.py:20-21` — a composite `Index(fields=["owner", "-updated_at"])` would avoid a per-user sort in #9. Its benefit is negligible on SQLite at this scale. — Reconsider only if profiling shows a need.

Security review (`security-reviewer`). Checked and found no issues:
- **Admin exposure:** staff only plus model permissions, and sign-up cannot create staff users.
- **`owner__username` search:** parameterised ORM `icontains`, with `select_related` for the owner column.
- **Cascade on user delete:** accepted for personal data.
- **Validation:** title and status rules are enforced. No secrets in the code.

Finding:
7. [low] `src/apps/goals/models.py:15` — `description` has no size limit, so a future form could accept bodies of several MB. That is a storage risk, and a cost risk once descriptions go to OpenAI. — Add a limit when the goal form arrives in #9: `max_length` on the field (enforced by ModelForm and `full_clean`), or a form validator.

## Requirements carried into #9 / #10 (from the security review)
- **[high if missed] IDOR:** every goal view requires login and fetches only through `Goal.objects.filter(owner=request.user)` (or `get_object_or_404(..., owner=request.user)`). Another user's goal returns 404, with tests for each verb, including POST to edit and delete.
- **[high if missed] Mass assignment:** the goal ModelForm has `fields = ["title", "description", "status"]`, never `owner`. The owner is set server-side in `form_valid`.
- **[medium] XSS:** escape title and description, using `|linebreaksbr` for line breaks. Never use `|safe`.
- **[medium] No GET side effects:** delete and status changes happen only on POST behind CSRF.
- **[low] Caching and size:** send `Cache-Control: private, no-store` on goal pages (see also #43), paginate the list, and cap the description size (finding 7).

## Reviewed
commit 83607c5, 2026-10-02

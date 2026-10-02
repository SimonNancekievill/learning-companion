# Review: user-profile

## Verdict: FAIL

The code reviewer reproduced one high-severity defect: the admin "Add user" page returns a 500 when the profile inline is filled in. There is also one medium: `loaddata` breaks on fixtures that contain profiles.

Everything else is fine. Every acceptance criterion is covered by a passing test, and the suite is green: 80 tests, also with `--shuffle` and `--reverse`. Lint, `manage.py check` and `makemigrations --check` are clean.

Following the workflow, nothing is fixed in this review. Findings 1, 2, 3, 5 and 6 are now plan steps 8–11. The remaining lows are recorded below for #7 and later tickets.

## Acceptance criteria
- AC1 — covered by `ProfileModelTests.test_profile_is_linked_one_to_one_to_the_user_and_cascades`, `test_profile_fields_may_be_blank_with_expected_limits`, `test_profile_migration_is_up_to_date` — PASS
- AC2 — covered by `ProfileAutoCreateTests.test_every_new_user_gets_exactly_one_empty_profile` — PASS
- AC3 — covered by `ProfileAutoCreateTests.test_saving_an_existing_user_again_creates_no_second_profile` — PASS
- AC4 — covered by `ProfileModelTests.test_deleting_a_user_deletes_their_profile` — PASS (precondition weak, see finding 5)
- AC5 — covered by `ProfileBackfillMigrationTests.test_backfill_creates_missing_profiles_and_keeps_existing_ones` — PASS (precondition weak, see finding 6)
- AC6 — covered by `ProfileFocusAreasTests.test_full_clean_rejects_malformed_focus_areas` — PASS (`None` untested, see finding 3)
- AC7 — covered by `ProfileFocusAreasTests.test_full_clean_trims_and_drops_case_insensitive_duplicates_in_order` — PASS
- AC8 — covered by `ProfileModelTests.test_str_names_the_user` — PASS
- AC9 — covered by `UserAdminTests.test_profile_is_an_inline_on_the_user_admin_and_not_registered_alone`, `test_user_change_page_shows_profile_fields` — PASS

## Findings
1. [high] `src/apps/accounts/admin.py:7-14` + `signals.py:10-11` — the admin **Add user** page also renders `ProfileInline`. If an admin fills in any profile field there, saving fails with a 500: `IntegrityError: UNIQUE constraint failed: accounts_profile.user_id`. The `post_save` receiver creates the profile first, then the inline formset inserts a second one. The code reviewer's probe reproduced this, and the security reviewer reported it independently (rated low, as availability). — Show the inline only on the change page (`get_inline_instances` returns `[]` when `obj is None`), with a test → **plan step 8**.
2. [medium] `src/apps/accounts/signals.py:10` — the receiver ignores `raw`. Running `loaddata` on a dump that contains users and their profiles fails with `IntegrityError`, because the signal already created a profile when the user row was loaded. Reproduced with `dumpdata accounts` followed by `loaddata`. Both reviewers reported it. — Skip raw saves, with a round-trip test → **plan step 9**.
3. [low] `src/apps/accounts/models.py:24-25` — clearing `focus_areas` in the admin submits `None`, and `clean()` rejects it as "not a list", even though the field is `blank=True`. `None` is untested. — Decide explicitly: treat `None` as empty and normalise it to `[]`, and lock that in with a test → **plan step 10**.
4. [low] `src/apps/accounts/models.py:22-33` — `clean()` always raises under the `focus_areas` key, so a future `ModelForm` that excludes that field would get a `ValueError`. — No change now. Keep it in mind for #7.
5. [low] `src/apps/accounts/tests.py:349-356` — since step 3, the cascade test's `get_or_create` is always a get, and the test never asserts that the profile existed before the delete. — Assert the profile exists first → **plan step 11** (test-only).
6. [low] `src/apps/accounts/tests.py:409-425` — the backfill test never asserts that "old" had no profile before migrating forward. — Add that precondition → **plan step 11** (test-only).
7. [low, security] `src/apps/accounts/models.py:17,22-33` — `focus_areas` has no limit on tag count or tag length, and the list rules only run in `full_clean()`, not on plain ORM saves. Today only admins can write the field. — Add count and length caps in #7, when a user-facing form arrives.
8. [low, security] `migrations/0003_backfill_profiles.py:7-9` — `bulk_create` loads every profile-less user at once, with no `batch_size`. This is fine at bootcamp scale. — Optional: `batch_size=1000` and iterate over pks.
9. [info] reversing `0002` drops the profile table and all its data. That is expected for a new model.

Forward-looking requirements for #7, from the security reviewer:
- Load the profile only as `request.user.profile`, behind login. Never take a pk from the URL.
- The `ProfileForm` lists its fields explicitly: no `__all__`, and never `user`.
- Render tags and name only through autoescaping (`json_script` if they are passed to JS), and treat them as untrusted input if they ever go into OpenAI prompts.
- Validate user input through the ModelForm, with the caps from finding 7, taking tags as a comma-separated text field rather than raw JSON.

## Reviewed
commit 965837a, 2026-10-02

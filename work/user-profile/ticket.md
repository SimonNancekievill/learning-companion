# Profile model

## Story
As a learner, I want every account to have a profile with my name, cohort and focus areas, so that the app can personalise my learning data and later AI suggestions.

## Acceptance criteria
- [ ] AC1 `apps.accounts.models.Profile` has a one-to-one link to `AUTH_USER_MODEL` (`related_name="profile"`, deleting the user deletes the profile) and these fields:
  - `name`: `CharField`, max 100, may be blank
  - `cohort`: `CharField`, max 50, may be blank
  - `focus_areas`: `JSONField`, default empty list, may be blank

  Its migration is committed and `makemigrations --check` reports no changes.
- [ ] AC2 Creating a user through any of these paths creates exactly one `Profile` for that user, with `name == ""`, `cohort == ""` and `focus_areas == []`:
  - `User.objects.create_user`
  - `User.objects.create_superuser`
  - a successful sign-up at `/accounts/signup/`
- [ ] AC3 Saving an existing user again creates no second profile and raises no error.
- [ ] AC4 Deleting a user deletes their profile.
- [ ] AC5 A data migration creates a profile, with the same empty defaults, for every user that existed without one before it ran, and leaves existing profiles untouched.
- [ ] AC6 `Profile.full_clean()` raises a `ValidationError` on `focus_areas` in either case:
  - the value is not a list
  - any item is not a string, or is empty after trimming whitespace
- [ ] AC7 `Profile.full_clean()` normalises `focus_areas`: it trims each tag and removes case-insensitive duplicates, keeping the first occurrence and the original order. For example, `[" Django ", "django", "SQL"]` becomes `["Django", "SQL"]`.
- [ ] AC8 `str(profile)` is `"<username>'s profile"`.
- [ ] AC9 In the Django admin, the user change page shows the profile's `name`, `cohort` and `focus_areas` as an inline (checked as a superuser: the page returns 200 and contains those fields). `Profile` has no separate admin registration.

## Out of scope
- A page where users view or edit their own profile (#7).
- Limits on the number or length of focus-area tags, and suggested or shared tag lists.
- Showing the profile name instead of the username in the nav.

## Notes
- Interview answers:
  - The model lives in the `accounts` app.
  - `focus_areas` is a `JSONField` holding a list of strings.
  - Profiles are created automatically by a `post_save` receiver on `User`, plus a backfill data migration for users that already exist.
  - The profile is edited as an inline on the User admin.
- `name` and `cohort` may be blank, because the profile is created empty at sign-up and filled in later (#7).
- SQLite has no array column. `JSONField` works on SQLite because Django uses its JSON1 support.
- The local `src/db.sqlite3` was recreated in #4 and has no real users. The backfill matters for any other environment.

# Goal model

## Story
As a learner, I want each of my learning goals stored with a title, description and status, so that later pages can list, filter and track them for me alone.

## Acceptance criteria
- [ ] AC1 A `goals` app exists as `apps.goals` (its `AppConfig.name` is `"apps.goals"`) and is registered in `INSTALLED_APPS`.
- [ ] AC2 `apps.goals.models.Goal` has these fields:
  - `owner`: a `ForeignKey` to `AUTH_USER_MODEL`, with `related_name="goals"` and `on_delete=CASCADE`
  - `title`: a `CharField`, max 200 characters, required
  - `description`: a `TextField` that may be blank
  - `status`: a `CharField` with choices from `Goal.Status`, a `TextChoices` whose values and labels are `planned`/"Planned", `in_progress`/"In progress" and `done`/"Done". It defaults to `planned`.
  - `created_at`: `auto_now_add`
  - `updated_at`: `auto_now`

  Its migration is committed, and `makemigrations --check` reports no changes.
- [ ] AC3 `created_at` and `updated_at` are set when a goal is created. Saving the goal again leaves `created_at` unchanged and moves `updated_at` forward.
- [ ] AC4 `Goal.full_clean()` rejects:
  - an empty title
  - a title longer than 200 characters
  - a `status` outside the three choices

  It accepts an empty description.
- [ ] AC5 Deleting a user deletes their goals and leaves other users' goals untouched.
- [ ] AC6 Goals are ordered by most recently updated first by default: after an older goal is saved again, it comes first in `user.goals.all()`.
- [ ] AC7 `str(goal)` is the goal's title.
- [ ] AC8 `Goal` is registered in the admin with:
  - `list_display` of title, owner, status and updated_at
  - `list_filter` on status
  - `search_fields` on title and the owner's username

  As a superuser, the goal changelist returns 200, and searching for a title shows only the matching goal.

## Out of scope
- Any user-facing goal pages: list, create, detail, edit, delete (#9, #10).
- The status filter on the list page (#11).
- Sessions and resources linked to goals (#12+).
- A unique title per user.

## Notes
- Interview answers:
  - `status` is a `TextChoices` enum, default `planned`.
  - The title is required and at most 200 characters; the description is optional; titles need not be unique.
  - Default ordering is `-updated_at`.
  - The admin gets list columns, a status filter and search.
- The owner field is called `owner`, with `related_name="goals"`. A user's goals are deleted with the user, because goals are personal learning data and nothing else references them yet.
- CLAUDE.md requires that every view showing goals is login-protected and filtered by the requesting user, with other users' goals returning 404. That applies to #9 and #10. This ticket only provides `user.goals` as the natural owner-scoped entry point.
- The status values `planned`, `in_progress` and `done` are what #11's `?status=` query parameter will use.

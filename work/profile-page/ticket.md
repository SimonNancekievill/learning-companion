# Profile page

## Story
As a logged-in learner, I want to view and edit my own name, cohort and focus areas on one page, so that my profile stays current without anyone else seeing or changing it.

## Acceptance criteria
- [x] AC1 An anonymous `GET /accounts/profile/` (URL name `accounts:profile`) redirects to the login page with `next=/accounts/profile/`. The route takes no parameters, so there is no user or profile id in the URL.
- [x] AC2 A logged-in `GET /accounts/profile/` returns 200 and renders `accounts/profile.html`, which extends `base.html`. It has the title "Profile" and a CSRF token. The form is pre-filled with the user's own `name` and `cohort`, and with `focus_areas` as comma-separated text (e.g. `Django, SQL`).
- [x] AC3 The form's fields are exactly `name`, `cohort` and `focus_areas`. A POST that also sends `user` or any other field cannot change which user the profile belongs to.
- [x] AC4 A valid POST saves the requesting user's profile and redirects to `/accounts/profile/`. The page then shows the message "Profile saved.". Focus areas are taken from the comma-separated text: blank pieces are ignored, then the model's trim and case-insensitive dedupe rules apply. For example, `"Django, , sql, SQL ,"` is saved as `["Django", "sql"]`.
- [x] AC5 The page only ever reads or writes the requesting user's profile. After user A posts, user B's profile is unchanged, and none of B's profile values appear on A's page.
- [x] AC6 A logged-in user who has no profile (for example, one loaded from a fixture without one) gets an empty profile created on their first visit, and the page returns 200.
- [x] AC7 `Profile.full_clean()` rejects more than 10 focus areas, or any focus area longer than 30 characters after trimming, with a `ValidationError` on `focus_areas`. The limit counts the tags after dedupe. Posting such input to the page re-renders it with status 200 and the error, and saves nothing.
- [x] AC8 Any other invalid POST (e.g. a `name` longer than 100 characters) re-renders the page with status 200 and the field error, and leaves the stored profile unchanged.
- [x] AC9 When logged in, the username in the nav is a link to `/accounts/profile/`.
- [x] AC10 `base.html` renders Django messages, so any page can show them, and the "Profile saved." message appears exactly once, on the page the redirect leads to.

## Out of scope
- Editing username, password or email.
- Viewing other users' profiles, or any public profile.
- Suggested tags, autocomplete, and a tag-chip UI.
- Showing the profile name instead of the username in the nav.

## Notes
- Interview answers:
  - One page that both shows and edits the profile, with a "Profile saved" message after saving.
  - Focus areas are entered as comma-separated text.
  - Limits: at most 10 tags, each at most 30 characters, enforced in `Profile.clean()` so the admin form and this page share the same rule.
  - The username in the nav becomes the link to the profile page.
- Requirements carried over from the #6 review (`work/user-profile/review.md`):
  - Load the profile only through `request.user`, with `get_or_create` (covers AC6), behind login, with no id in the URL.
  - The ModelForm lists its fields explicitly and never includes `user`.
  - All values are rendered through autoescaping.
  - The size caps apply in the model.
- The project rule (CLAUDE.md) is that another user's object returns 404, not 403. With no id in the URL, there is no way to address another user's profile at all.

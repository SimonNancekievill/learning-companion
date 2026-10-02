# Review: profile-page

## Verdict: PASS

- **Findings:** none high.
- **Acceptance criteria:** every one is covered by a passing test.
- **Checks:** the suite is green (98 tests, also with `--shuffle`). `ruff check`, `ruff format --check`, `manage.py check` and `makemigrations --check` are all clean.

The one medium finding (code review 1) is a test that asserts less than its name claims. The behaviour that AC3 and AC5 require is still asserted by that test: the owner is unchanged, the other user's profile is unchanged, and the other user's data is absent from the page. So it does not leave a criterion uncovered.

The medium and the lows are not fixed in this review. They are queued as the "Profile page hardening" backlog ticket.

## Acceptance criteria
- AC1 — covered by `ProfileLoginRequiredTests.test_anonymous_visitor_is_sent_to_login`, `ProfilePageTests.test_logged_in_user_sees_their_own_pre_filled_profile` (no URL kwargs) — PASS
- AC2 — covered by `ProfilePageTests.test_logged_in_user_sees_their_own_pre_filled_profile`, `ProfileFormTests.test_focus_areas_are_shown_as_comma_separated_text` — PASS
- AC3 — covered by `ProfileFormTests.test_form_edits_exactly_name_cohort_and_focus_areas`, `ProfilePageTests.test_only_the_requesting_users_profile_is_read_or_written` — PASS
- AC4 — covered by `ProfileFormTests.test_comma_separated_text_is_saved_as_a_clean_list`, `ProfilePageTests.test_valid_post_saves_own_profile_and_redirects_back`, `test_saved_message_is_shown_exactly_once` — PASS
- AC5 — covered by `ProfilePageTests.test_only_the_requesting_users_profile_is_read_or_written` — PASS (weak on the "new values saved" half, see finding 1)
- AC6 — covered by `ProfilePageTests.test_user_without_a_profile_gets_one_on_first_visit` — PASS
- AC7 — covered by `ProfileFocusAreasTests.test_full_clean_caps_focus_areas_at_ten_tags_of_thirty_characters`, `ProfilePageTests.test_too_many_or_too_long_tags_show_an_error_and_save_nothing` — PASS
- AC8 — covered by `ProfilePageTests.test_other_invalid_input_shows_the_error_and_saves_nothing` — PASS
- AC9 — covered by `NavTests.test_logged_in_username_links_to_the_profile_page`, `test_anonymous_nav_has_no_profile_link` — PASS
- AC10 — covered by `ProfilePageTests.test_saved_message_is_shown_exactly_once`, `test_base_layout_renders_messages_for_any_page` — PASS

## Findings
Code review (`code-reviewer`). Its probes confirmed that a bound form re-renders the user's submitted text and not the old value, that a null character in the input re-renders cleanly, that messages render only once, and that the admin inline honours the caps.

1. [medium] `src/apps/accounts/tests.py` (`test_only_the_requesting_users_profile_is_read_or_written`) — the test posts the same name and cohort that `setUp` already stored, and asserts neither the redirect nor `focus_areas`. So "ada's profile has the new values" is never really tested. If `user` were ever added to the form, the smuggled `bob.pk` would fail validation, nothing would save, and the test would stay green. — Post values that differ from `setUp`, and assert the redirect and all three fields.
2. [low] `src/apps/accounts/forms.py:22,26` — tags containing a comma do not survive the comma-separated round trip. A tag such as `"C, C++"`, set through the admin, would be silently split on the next save from the page. — Reject commas inside tags in `Profile.clean()`, so admin and page share the rule.
3. [low] `src/apps/accounts/models.py:38-42` — input that has too many tags *and* a tag that is too long only reports the count error. The length error appears only after a second submit. — Collect both messages into one `ValidationError`.
4. [low] `src/apps/accounts/models.py:38-42` — the new caps also apply to existing over-limit data, which would block saving on the page and in the admin until trimmed. There is no production data yet. — Noted only.
5. [low] `src/templates/base.html:31-33` — every message is styled green whatever its level. — Pick the classes from `message.tags`.

Security review (`security-reviewer`). These were checked and found fine:
- IDOR: only `request.user`, with no id in the URL, and `LoginRequiredMixin` runs before `get_object`.
- No mass assignment: the fields are explicit and there is no `user` field.
- Autoescaping of the form, the username and messages; `success_message` contains no user input.
- The caps are enforced via `ModelForm._post_clean`.
- `get_or_create`, including two concurrent first visits.
- CSRF protection, no open redirect, and no secrets.

6. [low] `src/apps/accounts/views.py:28` — no `Cache-Control: private, no-store` on the first page that shows user data (recommended in `work/auth-login-logout/review.md`, finding 10). — Add `never_cache` (or a middleware for authenticated responses), with a header test.
7. [low] `src/apps/accounts/forms.py:13,27` — the `focus_areas` text has no length limit, so a ~2.5 MB body is split and normalised before the caps reject it. That is wasted CPU and memory, not a real DoS, and it needs login plus CSRF. — Add `max_length` to the form field, e.g. `MAX_FOCUS_AREAS * (MAX_FOCUS_AREA_LENGTH + 2)`.

Process note: the code reviewer briefly copied a probe file into `src/apps/accounts/` and deleted it within the same command. It was never run or committed, and `git status` was verified clean at HEAD 4d8cf2b after the review.

## Reviewed
commit 4d8cf2b, 2026-10-02

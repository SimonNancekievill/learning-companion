# Sign up

## Story
As a visitor, I want to create an account with a username and password and be logged in straight away, so that I can start tracking my learning without a separate login step.

## Acceptance criteria
- [ ] AC1 An `accounts` app exists as `apps.accounts` (its `AppConfig.name` is `"apps.accounts"`) and is registered in `INSTALLED_APPS`.
- [ ] AC2 `AUTH_USER_MODEL` is `"accounts.User"`, a custom user model subclassing `AbstractUser` with no extra fields, and its initial migration is committed.
- [ ] AC3 The custom `User` is registered in the Django admin.
- [ ] AC4 `GET /accounts/signup/` (URL name `accounts:signup`) returns 200 for an anonymous visitor and renders `accounts/signup.html`, which extends `base.html`.
- [ ] AC5 The sign-up form is based on Django's `UserCreationForm`, bound to the custom `User`, and asks for exactly username, password and password confirmation.
- [ ] AC6 A valid `POST` creates exactly one user with that username and a usable, hashed password (the raw password is not stored).
- [ ] AC7 After a valid `POST` the new user is logged in (the session belongs to that user) and is redirected to `/`.
- [ ] AC8 An invalid `POST` (e.g. mismatched passwords, a password rejected by the configured validators, or a username that already exists) creates no user, returns 200, re-renders the form, and shows the form's error messages.
- [ ] AC9 The form includes a CSRF token, and the page sets the `title` block to "Sign up".
- [ ] AC10 An already logged-in user who requests the page by `GET` or `POST` is redirected to `/`; no user is created and the current session is not changed.

## Out of scope
- Log in / log out views and the auth-dependent nav links (#5). This ticket adds no nav link to the sign-up page.
- Profile data (name, cohort, focus areas) and its automatic creation (#6).
- Email address, email verification, password reset.
- Custom styling beyond basic Tailwind utility classes on the form.

## Notes
- Interview answers:
  - Introduce a custom user model now, because the project has no migrations yet and swapping it later is painful.
  - The form asks for username + password only.
  - The page lives at `/accounts/signup/` and redirects to `/` on success.
  - Logged-in users are redirected to `/`.
- `CLAUDE.md` says to use Django's built-in auth only (`django.contrib.auth`, no third-party package), and the app layout should be `src/apps/accounts/` registered as `apps.accounts`.
- These tests need the database (user creation), so they use `django.test.TestCase`. The `core` tests use `SimpleTestCase`.
- The 4 standard `AUTH_PASSWORD_VALIDATORS` are already configured and apply to the form.
- `instructions/challenge.md` only asks to "confirm you can sign up, log out, and log back in". The log-out and log-in half of that is #5.

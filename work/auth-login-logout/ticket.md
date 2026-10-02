# Log in and log out

## Story
As a registered user, I want to log in and log out and always see my auth state in the navigation, so that I can come back to my learning data and leave a shared computer safely.

## Acceptance criteria
- [ ] AC1 `GET /accounts/login/` (URL name `accounts:login`) returns 200 for an anonymous visitor and renders `accounts/login.html`, which extends `base.html`. The page has a CSRF token and the title "Log in", and is built on Django's built-in `LoginView`.
- [ ] AC2 A `POST` with valid credentials logs that user in (the session belongs to them) and redirects to `/`.
- [ ] AC3 A valid `POST` with a safe `next` (e.g. `?next=/accounts/signup/`) redirects there. An unsafe external `next` (e.g. `https://evil.example/`) is ignored and the user goes to `/`.
- [ ] AC4 A `POST` with wrong credentials returns 200, logs nobody in, and shows Django's "correct username and password" error.
- [ ] AC5 An already logged-in user who opens the login page is redirected to `/`.
- [ ] AC6 `settings.LOGIN_URL` resolves to `/accounts/login/`, and `LOGIN_REDIRECT_URL` and `LOGOUT_REDIRECT_URL` resolve to `/`.
- [ ] AC7 `POST /accounts/logout/` (URL name `accounts:logout`) logs the user out and redirects to `/`. A `GET` to the same URL does not log out (405, session unchanged).
- [ ] AC8 For an anonymous visitor, the nav (inside `<header>`) shows a "Log in" link to `/accounts/login/` and a "Sign up" link to `/accounts/signup/`, and no log-out control.
- [ ] AC9 For a logged-in user, the nav shows their username and a "Log out" button inside a `POST` form to `/accounts/logout/` that includes a CSRF token. It shows no "Log in" or "Sign up" links.
- [ ] AC10 The login page links to the sign-up page ("No account yet? Sign up"), and the sign-up page links to the login page ("Already have an account? Log in").
- [ ] AC11 End-to-end, a visitor can sign up, log out and log back in with the same credentials, ending up logged in as that user.

## Out of scope
- Password reset and password change.
- A profile page or link (#7); the username in the nav is plain text.
- Rate limiting or lockout of failed logins (#36 Auth hardening).
- "Remember me" or custom session lengths.

## Notes
- Interview answers:
  - After both login and logout the user lands on `/`; a safe `?next=` still wins after login.
  - A logged-in user who opens the login page is redirected to `/`, the same as on the sign-up page.
  - Nav when logged out: "Log in" and "Sign up" links. Nav when logged in: the username as plain text plus a "Log out" button, and nothing else.
  - The login and sign-up pages link to each other in both directions.
- `CLAUDE.md` says to use Django's built-in auth views only, with no third-party package.
- Since Django 5, `LogoutView` only accepts `POST`, so logging out must be a form with a button, not a link.
- `base.html` already has an empty `nav` block inside `<header>` that this ticket fills. The sign-up page from #4 lives at `/accounts/signup/` and redirects logged-in users to `/`.
- AC11 covers the assignment's check in `instructions/challenge.md`: "Confirm you can sign up, log out, and log back in."

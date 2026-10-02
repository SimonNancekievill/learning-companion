# Ticket backlog

Queue for `factory-manager`, kept in sync with the GitHub issues and project board by
`scripts/board.sh`. One ticket per line, top to bottom = priority order. Add new ideas
as plain `- [ ] <title>: <description>` lines (or as issues on the board); the issue
number, status and ticket id are filled in by the pipeline — leave them alone.

- [x] #1 (Done) env-settings: Settings from environment: read SECRET_KEY, DEBUG and ALLOWED_HOSTS from `.env` via django-environ (add to requirements.txt), no secrets left in settings.py, `.env.example` documents every variable — work/env-settings/review.md
- [x] #2 (Done) ci-pipeline: CI pipeline: GitHub Actions workflow that installs requirements-dev.txt and runs `ruff check`, `ruff format --check` and the Django test suite on every push and on pull requests into develop and main — work/ci-pipeline/review.md
- [x] #3 (Done) base-layout: Base layout and home page: `core` app with a `base.html` template styled with Tailwind via django-tailwind-cli, and a home page at `/` that renders it — work/base-layout/review.md
- [x] #4 (Done) accounts-signup: Sign up: `accounts` app with a sign-up page using Django's UserCreationForm that creates the user and logs them in — work/accounts-signup/review.md
- [~] #5 (Refined) auth-login-logout: Log in and log out: Django's built-in auth views; the navigation shows log in / sign up or the username and log out depending on auth state
- [ ] #6 (Todo) Profile model: linked one-to-one to the user with `name`, `cohort` and a list of `focus_area` tags, created automatically for every new user
- [ ] #7 (Todo) Profile page: view and edit your own profile, login required, never shows another user's data
- [ ] #8 (Todo) Goal model: `goals` app with `title`, `description`, `status` (planned / in-progress / done), `created_at`, `updated_at`, owned by a user, with migration and admin registration
- [ ] #9 (Todo) Goal list and create: logged-in users see only their own goals and can create a new one
- [ ] #10 (Todo) Goal detail, edit and delete: scoped to the owner, other users' goals return 404
- [ ] #11 (Todo) Goal status filter: filter the goal list by `status` via a query parameter and a filter control on the list page
- [ ] #12 (Todo) LearningSession model: linked to a Goal with `date`, `duration`, `notes` and `tags`, with migration and admin registration
- [ ] #13 (Todo) LearningSession CRUD: create, edit and delete sessions from the goal detail page, sessions listed on the goal detail, scoped to the goal's owner
- [ ] #14 (Todo) Resource model: linked to a Goal with `url`, `title`, `type` (article / video / repo / doc), with migration and admin registration
- [ ] #15 (Todo) Attach resource form: attach a resource to a goal with a form on the goal detail page, scoped to the goal's owner
- [ ] #16 (Todo) Resources on goal detail: show a goal's resources on its detail page, grouped or badged by `type`
- [ ] #17 (Todo) OpenAI client service: OPENAI_API_KEY read from `.env`, a thin wrapper around the Chat Completions API that tests replace with a fake (no network in tests)
- [ ] #18 (Todo) Generate summary action: on the goal detail page, send recent sessions and resources to the OpenAI service and display the returned progress summary
- [ ] #19 (Todo) Suggest next steps action: on the goal detail page, send the goal and its past sessions and render 2-3 concrete next learning actions as a list
- [ ] #20 (Todo) Dashboard goals per status: dashboard page showing the count of the user's goals per `status` using ORM aggregation
- [ ] #21 (Todo) Dashboard hours per tag: total logged session hours per tag using `annotate`/`aggregate`, rendered as a table or bars
- [ ] #22 (Todo) Dashboard hours per week: total logged session hours per week using ORM aggregation, rendered as a table or bars
- [ ] #23 (Todo) Dockerfile: Python base image, builds Tailwind CSS, collects static files, serves the app with gunicorn, SQLite database on a mounted volume; `docker build` + `docker run` serves the app
- [ ] #24 (Todo) Docker image in CI: build the Docker image in the GitHub Actions workflow on pull requests into develop and main
- [ ] #26 (Todo) Harden guard-bash.sh: make the commit/push guard robust: detect --no-verify/-n and abbreviated --no-v* anywhere in the git commit args (ignoring quoted messages and heredocs, not cut at ;&|), recognise git with global options (-c, -C, --git-dir), env/command prefixes, absolute paths and bash -c/subshells, block core.hooksPath overrides and +refspec force-pushes to protected branches, and add a self-test script covering these cases (findings from work/env-settings/review.md)
- [ ] #29 (Todo) CI hardening: least-privilege `permissions: contents: read` in ci.yml, actions pinned to commit SHAs with Dependabot for github-actions, `persist-credentials: false` on checkout, `app_id` (GitHub Actions) on the required lint/test checks in board.sh protect, fail-closed env for the board.sh protect test, and document or replace the admin-bypass push of the main->develop merge-back (findings from work/ci-pipeline/review.md)
- [ ] #33 (Todo) Base layout hardening: verify the Tailwind CLI binary against the release sha256sums before CI runs it (TAILWIND_CLI_AUTOMATIC_DOWNLOAD off, TAILWIND_CLI_PATH to the verified binary) and cache it by version; tighten the base-layout tests (assert src/assets/.gitkeep itself, cut <head>/<main> with the asserting element() helper, assert base.html origin is TEMPLATES DIRS, attribute-order independent header-link regex) (findings from work/base-layout/review.md)
- [ ] #36 (Todo) Auth hardening: per-IP rate limit (or CAPTCHA) on /accounts/signup/ before the AI features ship, optional username character-set normalisation against homoglyphs, secure cookie/HSTS/SSL-redirect settings from env with `check --deploy` in CI, throttled admin login, and tighten the AC8 sign-up subtests to assert the expected error field per case (findings from work/accounts-signup/review.md)

# Learning Companion

A Django app for tracking learning goals and sessions, attaching resources, and getting AI-powered summaries and next steps. Built ticket by ticket through the AI factory pipeline in `.claude/` (see `docs/ai-factory-workflow.md`). The original assignment is in `instructions/`.

## Stack

- Python 3.14, Django 6.1, Django's built-in test runner (`django.test.TestCase`)
- Server-rendered Django templates styled with Tailwind CSS via `django-tailwind-cli` (standalone Tailwind binary, no Node)
- SQLite in every environment, including the container (mounted volume)
- Django's built-in auth (`django.contrib.auth`), no third-party auth package
- Configuration from `.env` via `django-environ`; never hardcode secrets or the OpenAI API key
- OpenAI Chat Completions API through the `openai` SDK, wrapped in a service that tests replace with a fake
- Ruff for linting and formatting (config in `pyproject.toml`)

Add a dependency to `requirements.txt` (runtime) or `requirements-dev.txt` (tooling) in the ticket that first needs it, pinned to an exact version.

## Commands

Run from the repo root:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt   # setup
.venv/bin/python src/manage.py runserver                                 # dev server
.venv/bin/python src/manage.py test src                                  # test suite
.venv/bin/python src/manage.py makemigrations && .venv/bin/python src/manage.py migrate
.venv/bin/ruff check . && .venv/bin/ruff format --check .                # lint
```

`manage.py test` without the `src` argument finds no tests when run from the repo root.

## Layout

- `src/manage.py`, `src/config/` — project package (settings, root URLs, WSGI/ASGI)
- `src/apps/<name>/` — one Django app per domain area (`core`, `accounts`, `goals`, ...), created with `../.venv/bin/python manage.py startapp <name> apps/<name>` from `src/`, registered as `apps.<name>` in `INSTALLED_APPS` (set `name = "apps.<name>"` in its `AppConfig`)
- Tests live in each app as `tests/` package or `tests.py`
- Templates per app under `src/apps/<name>/templates/<name>/`; shared templates (`base.html`) under `src/templates/`
- `work/` — workflow artifacts: `backlog.md`, and `work/<ticket-id>/` with `ticket.md`, `plan.md`, `review.md`

Everything under `src/` is write-protected outside the `implementing` phase.

## Conventions

- Every view that shows user data requires login and filters by the requesting user; another user's object returns 404, not 403.
- Branches, commit messages and PR targets: `.claude/rules/git.md` and `.conventionalcommit.json`. Gitflow: `feature/<id>` / `fix/<id>` off `develop` → squash-merged PR into `develop` → `main` merged back into `develop` → merge-commit release PR `develop` → `main`. `main` is protected.

## Ticket tracking

Each ticket exists three times and they must agree: a line in `work/backlog.md`, a GitHub issue, and a card on the GitHub project board (ids in `work/board.json`). `scripts/board.sh` keeps them in sync:

```bash
bash scripts/board.sh setup                     # once: merge settings and project board
bash scripts/board.sh protect                   # once, after main and develop are pushed: branch protection
bash scripts/board.sh sync                      # new backlog lines -> issues; new board issues -> backlog
bash scripts/board.sh status <issue> "<status>" # the only way to change a ticket's status
```

Statuses: Todo → Refined → Planned → In progress → In review → In develop → Done (on `main`).

# Settings from environment

## Story
As the developer deploying Learning Companion, I want SECRET_KEY, DEBUG and ALLOWED_HOSTS to come from the environment or a `.env` file, so that no secret is committed and each environment (local, CI, container) is configured without editing `settings.py`.

## Acceptance criteria
- [x] AC1 `SECRET_KEY` equals the value of `DJANGO_SECRET_KEY` from the environment.
- [x] AC2 Loading settings without `DJANGO_SECRET_KEY` raises `django.core.exceptions.ImproperlyConfigured`. There is no fallback key.
- [x] AC3 `DEBUG` is `True` when `DJANGO_DEBUG` is a truthy value (e.g. `true`, `1`). It is `False` when the variable is falsy (e.g. `false`, `0`) or unset.
- [x] AC4 `ALLOWED_HOSTS` is the comma-separated list from `DJANGO_ALLOWED_HOSTS` (e.g. `localhost,127.0.0.1` → `["localhost", "127.0.0.1"]`). It is `[]` when the variable is unset.
- [x] AC5 Values in a `.env` file at the repo root are picked up when the process environment doesn't set them.
- [x] AC6 A variable already set in the process environment takes precedence over the same variable in `.env`.
- [x] AC7 Settings load without a `.env` file as long as the required variables are in the process environment (container / CI case).
- [x] AC8 `src/config/settings.py` contains no hardcoded secret key literal (no `django-insecure-` string).
- [x] AC9 `django-environ` is pinned to an exact version in `requirements.txt`.
- [x] AC10 `.env.example` documents every variable the settings read (`DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`), each with a comment and a safe placeholder. `OPENAI_API_KEY` stays as a documented placeholder. The stale "not read by settings.py yet" note is removed.

## Out of scope
- Reading `OPENAI_API_KEY` into settings (ticket #17).
- Configuring the database from the environment (SQLite at a fixed path stays as is).
- `STATIC_ROOT`, production security headers, and Docker or CI wiring (tickets #2, #23, #24).

## Notes
- Interview answers:
  - A missing secret key fails loudly.
  - `DEBUG` and `ALLOWED_HOSTS` default to the safe values (`False` and `[]`).
  - Variable names keep the `DJANGO_` prefix that `.env.example` already uses.
  - `OPENAI_API_KEY` is documented only.
- Current state: `settings.py` is stock `startproject` output with a committed `django-insecure-` key, `DEBUG = True` and `ALLOWED_HOSTS = []`. `.env` is already in `.gitignore`, and there is no `.env` on disk. There are no tests yet.
- `BASE_DIR` is `src/`, so the repo-root `.env` is at `BASE_DIR.parent / ".env"`.
- Once AC2 lands, the test suite and `runserver` need `DJANGO_SECRET_KEY` set, either from a local `.env` or the environment. The CI ticket (#2) has to provide it.

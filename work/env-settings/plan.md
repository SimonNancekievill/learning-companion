# Plan: env-settings

## Research summary
- **Settings:** `src/config/settings.py` is stock `startproject` output (Django 6.1.1).
  - `BASE_DIR = Path(__file__).resolve().parent.parent` resolves to `src/`, so the repo-root `.env` is `BASE_DIR.parent / ".env"`.
  - L23 is a hardcoded `django-insecure-` key, L26 is `DEBUG = True`, L28 is `ALLOWED_HOSTS = []`.
  - The file imports nothing besides `pathlib.Path`.
- **django-environ 0.14.0** is the latest release. It supports Python 3.14, lists Django up to 6.0, and was verified working with 6.1.1.
  - `Env.read_env(path)` defaults to `overwrite=False` and uses `setdefault`, so values already in the process environment win.
  - If the file is missing, `read_env` only calls `logger.info`. It raises nothing.
  - `env("X")` with no default raises `django.core.exceptions.ImproperlyConfigured`.
  - `env.bool` treats `true/on/ok/y/yes` and non-zero ints as true, case-insensitive. Anything else is false. A default is returned unparsed.
  - `env.list` splits on `,` and drops empty items but does **not** strip whitespace. Pass `cast=str.strip` to strip each item.
  - Gotcha: a value starting with `$` is treated as a reference to another variable.
- **Test discovery:** `manage.py test src` uses `src/` as the top level, because `src/__init__.py` doesn't exist.
  - `src/config/tests/__init__.py` + `test_settings.py` is discovered as `config.tests.test_settings`.
  - Run one file with `.venv/bin/python src/manage.py test config.tests.test_settings` (from repo root; `src/` is on sys.path).
- **Testing settings:** settings are already loaded when tests run, so tests must not reload the live `config.settings`. They execute a *copy* of the module instead (see Design decisions).
- **Hooks:** `.claude/hooks/config.sh` sets `TEST_CMD=".venv/bin/python src/manage.py test src --verbosity 0"`. No hook provides `DJANGO_SECRET_KEY`.
  - **Known hook bug, outside this ticket:** `post-write.sh` and `guard-bash.sh` only run tests when `package.json` exists, so `last_test` is never updated. During implementation, confirm red and green by running the suite by hand at every step.
- **Lint:** ruff, line length 100, rules `E,F,W,I,B,UP,DJ`, double quotes.

## Design decisions
- **Helper `load_settings(env: dict[str, str], dotenv: str | None = None) -> dict`** lives in `src/config/tests/test_settings.py`.
  - It copies `src/config/settings.py` into a temp tree `<tmp>/src/config/settings.py`, with `<tmp>/.env` written only if `dotenv` is given.
  - It runs the copy with `runpy.run_path` under `mock.patch.dict(os.environ, env, clear=True)` and returns the module globals.
  - Rationale: the developer's real `.env` and process environment can't leak into the tests, `.env` precedence is exercised for real, and no extra "env file path" variable is needed.
- **`.env` is read in the same step that makes `SECRET_KEY` required.** Without it, the test suite itself (`manage.py test`) couldn't start. A local, gitignored `.env` copied from `.env.example` is a prerequisite from step 2 on.
- **`ALLOWED_HOSTS` items are whitespace-stripped** (`cast=str.strip`), so `localhost, 127.0.0.1` works too.
- **Guard tests in step 3:** some ACs are already satisfied by the minimal implementation of step 2. They are added as regression tests that pass on arrival, committed as `test(env-settings): ...`. This is the one deliberate exception to the "red first" rule, which only applies to behaviour changes.
- **Repo-file tests** (requirements, `.env.example`) resolve the repo root as `Path(__file__).resolve().parents[3]`.

## Steps
- [x] 1. `requirements.txt` pins `django-environ` to an exact version
  - test: `src/config/tests/test_settings.py` (create the `src/config/tests/__init__.py` package). The test asserts a line matching `django-environ==<x.y.z>`.
  - impl: add `django-environ==0.14.0` to `requirements.txt`, then `.venv/bin/pip install -r requirements-dev.txt`.
  - covers: AC9
- [x] 2. `SECRET_KEY` is read from a repo-root `.env` when the process environment lacks it
  - test: `load_settings({}, dotenv="DJANGO_SECRET_KEY=from-file")["SECRET_KEY"] == "from-file"`. It is red because the hardcoded literal is still returned.
  - impl: `src/config/settings.py` creates an `environ.Env()`, calls `read_env(BASE_DIR.parent / ".env")`, sets `SECRET_KEY = env("DJANGO_SECRET_KEY")` and deletes the literal.
  - prerequisite before running green: `cp .env.example .env` locally (gitignored, never committed).
  - covers: AC5, AC1, AC8
- [ ] 3. Guard tests (pass on arrival, `test(...)` commit)
  - (a) `DJANGO_SECRET_KEY` in the process environment is used.
  - (b) A missing key raises `ImproperlyConfigured`.
  - (c) The process environment beats `.env` for the same variable.
  - (d) Settings load without any `.env` file when the key is in the process environment.
  - (e) The `settings.py` source contains no `django-insecure-`.
  - test: `src/config/tests/test_settings.py`
  - impl: none
  - covers: AC1, AC2, AC6, AC7, AC8
- [ ] 4. `DEBUG` comes from `DJANGO_DEBUG` and defaults to `False`
  - test: one test with subTests: `true`/`1` → `True`, `false`/`0` → `False`, unset → `False`. It is red on the unset case.
  - impl: `DEBUG = env.bool("DJANGO_DEBUG", default=False)` in `settings.py`.
  - covers: AC3
- [ ] 5. `ALLOWED_HOSTS` comes from the comma-separated `DJANGO_ALLOWED_HOSTS` and defaults to `[]`
  - test: subTests: `localhost,127.0.0.1` → `["localhost", "127.0.0.1"]`, `localhost, 127.0.0.1` → same, unset → `[]`. It is red on the first case.
  - impl: `ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", cast=str.strip, default=[])`.
  - covers: AC4
- [ ] 6. `.env.example` documents every variable the settings read
  - test: for each of `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, a `NAME=` line exists and is directly preceded by a `#` comment line. `OPENAI_API_KEY=` is present. The text "not read by" is absent. It is red because the stale note is still there.
  - impl: rewrite the `.env.example` comments and remove the stale note. Mention generating a key with `secrets.token_urlsafe(50)`, since values starting with `$` are treated as references. Add `cp .env.example .env` to the setup command in `CLAUDE.md`.
  - covers: AC10

## Coverage
| AC | Steps |
|----|-------|
| AC1 | 2, 3a |
| AC2 | 3b |
| AC3 | 4 |
| AC4 | 5 |
| AC5 | 2 |
| AC6 | 3c |
| AC7 | 3d |
| AC8 | 2, 3e |
| AC9 | 1 |
| AC10 | 6 |

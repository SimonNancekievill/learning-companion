# Plan: ci-pipeline

## Research summary
- **Repo state:**
  - There is no `.github/` yet.
  - `.python-version` = `3.14`.
  - `requirements-dev.txt` = `-r requirements.txt` + `ruff==0.16.9`.
  - The only required env var is `DJANGO_SECRET_KEY`. SQLite needs no service.
- **Actions (as of 2026-10-01):**
  - **Versions:** `actions/checkout@v7` and `actions/setup-python@v7`. Python 3.14 (up to 3.14.8) is available on `ubuntu-latest`.
  - **`python-version-file`:** `.python-version` is supported. An explicit `python-version` would override it.
  - **`cache: pip`:** it keys on `**/requirements.txt` only, unless `cache-dependency-path` lists `requirements-dev.txt` too.
  - **Masking:** values written to `$GITHUB_ENV` are not masked. Emit `::add-mask::<value>` first.
  - **Check names:** the check context of a job without `name:` is its job id, so `lint` and `test`.
- **YAML parsing in tests:**
  - The stdlib has no YAML parser. `PyYAML==6.0.3` has cp314 wheels (macOS arm64 and manylinux).
  - Gotcha: under YAML 1.1, `yaml.safe_load` parses the key `on:` as boolean `True`. Read the triggers via `data[True]`, and keep `on:` unquoted in the workflow, as is conventional.
- **`scripts/board.sh protect` (L175–203):**
  - It gets `owner` and `repo` via `gh repo view --json owner|name --jq ...`. It then sends two `gh api -X PUT repos/<o>/<r>/branches/{main,develop}/protection --input -` calls, with a quoted `<<'JSON'` heredoc as stdin.
  - Both payloads currently have `"required_status_checks": null`.
  - main: `enforce_admins: true`, PR required with 0 approvals. develop: `enforce_admins: false`, no PR requirement. Both: `restrictions: null`, no force-push, no deletions.
  - The script uses `set -euo pipefail` and bare `gh` calls (no absolute path, no `command -v`), so a fake `gh` first on `PATH` can capture argv and stdin.
- **Tests:** they go in `src/config/tests/test_ci.py` (Django `SimpleTestCase`), with repo root `Path(__file__).resolve().parents[3]`, as in `test_settings.py`. Run with `.venv/bin/python src/manage.py test config.tests.test_ci`.
- **Hooks:** writes to `.github/` and `scripts/` are outside `SOURCE_DIRS`, so the post-write hook doesn't re-run the suite after them. Confirm green by hand after every implementation write.

## Design decisions
- **PyYAML goes into `requirements-dev.txt`**, not runtime: only the tests need it, and CI installs the dev file anyway.
- **One test module, `test_ci.py`**, with helpers `workflow() -> dict` (safe_load of `.github/workflows/ci.yml`) and `steps(job) -> list[dict]`. Assertions look at `run:` strings and `uses:`/`with:` of the steps. They don't depend on step names or step order, so the workflow can be restyled freely.
- **The protect test runs the real script** (`subprocess.run(["bash", "scripts/board.sh", "protect"], cwd=REPO_ROOT)`) with a temp dir first on `PATH`.
  - The fake `gh` there answers `repo view` with `acme` / `proj`.
  - It saves each `api` call's argv and stdin as numbered files.
  - The test then `json.loads` both payloads.
  - It needs no network and no auth.
- **Payload format:** `required_status_checks` = `{"strict": false, "checks": [{"context": "lint"}, {"context": "test"}]}`. `checks` is the current API form; `contexts` is deprecated. `strict: false` because requiring up-to-date branches is out of scope.
- **Secret key step:** it generates `secrets.token_urlsafe(50)`, masks it, and appends it to `$GITHUB_ENV`. It runs only in the `test` job, because `lint` doesn't import settings.
- **AC8 can't be checked before the PR exists.** CI only runs once the branch is pushed, and the push gate opens after `final-review` PASS. `final-review` records AC8 as "verified at delivery". `factory-manager` already refuses to merge on failing or pending checks (`gh pr checks`), and parks on failure, so AC8 is enforced before the PR lands. A red CI run sends the ticket back through `tdd-implement`.

## Steps
- [x] 1. `requirements-dev.txt` pins PyYAML to an exact version
  - test: `src/config/tests/test_ci.py` asserts a line matching `PyYAML==<x.y.z>`.
  - impl: add `PyYAML==6.0.3` to `requirements-dev.txt`, then `.venv/bin/pip install -r requirements-dev.txt`.
  - covers: prerequisite for AC1–AC6
- [x] 2. The workflow file exists and parses as a YAML mapping with a `jobs` mapping
  - test: `workflow()` returns a dict and `"jobs"` is a dict. It is red because the file is missing.
  - impl: `.github/workflows/ci.yml` with `name: CI` and an empty `jobs: {}`.
  - covers: AC1
- [ ] 3. Triggers
  - test: `workflow()[True]` has a `push` key with no `branches` filter, and `pull_request.branches` equals `{"develop", "main"}`.
  - impl: the `on:` block in `ci.yml`.
  - covers: AC2
- [ ] 4. `lint` job
  - test: job `lint` exists, runs on `ubuntu-latest`, and its `run:` steps include `pip install -r requirements-dev.txt`, `ruff check .` and `ruff format --check .`.
  - impl: the `lint` job in `ci.yml`, with checkout, install, check and format-check.
  - covers: AC3
- [ ] 5. `test` job
  - test: job `test` exists, runs on `ubuntu-latest`, and its `run:` steps include `pip install -r requirements-dev.txt` and `python src/manage.py test src`.
  - impl: the `test` job in `ci.yml`.
  - covers: AC4
- [ ] 6. Python from `.python-version` with pip cache
  - test: both jobs have an `actions/setup-python@v7` step whose `with` has `python-version-file: .python-version`, no `python-version`, `cache: pip`, and a `cache-dependency-path` that mentions `requirements-dev.txt`.
  - impl: add the setup-python step to both jobs.
  - covers: AC5
- [ ] 7. Per-run secret key in the `test` job
  - test:
    - A step before the `manage.py test` step has a `run:` that contains `secrets.token_urlsafe`, `::add-mask::` and `>> "$GITHUB_ENV"`.
    - The workflow text contains no `secrets.` expression.
    - No job or step `env:` sets `DJANGO_SECRET_KEY` to a literal.
  - impl: add the generate-key step to `test`.
  - covers: AC6
- [ ] 8. `board.sh protect` requires `lint` and `test` on main and develop
  - test: run the script with the fake `gh`.
    - It must make exactly two `api` calls, to `repos/acme/proj/branches/main/protection` and `.../develop/protection`.
    - Both payloads have `required_status_checks == {"strict": False, "checks": [{"context": "lint"}, {"context": "test"}]}`.
    - All other keys equal today's values, listed in the research summary.
  - impl: edit both heredocs in `scripts/board.sh` and the `echo` lines, and mention required checks in the usage header.
  - covers: AC7
- [ ] AC8 has no step. It is verified on the ticket PR by `gh pr checks` at delivery (see Design decisions).

## Coverage
| AC | Steps |
|----|-------|
| AC1 | 2 |
| AC2 | 3 |
| AC3 | 4 |
| AC4 | 5 |
| AC5 | 6 |
| AC6 | 7 |
| AC7 | 8 |
| AC8 | delivery gate (`gh pr checks` on the ticket PR) |

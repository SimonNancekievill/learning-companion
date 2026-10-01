# CI pipeline

## Story
As the developer running the AI factory, I want a GitHub Actions workflow that lints and tests every push and every PR into `develop` and `main`, and that branch protection enforces, so that nothing red can reach `develop` or `main`, whether it's merged by `factory-manager` or by hand.

## Acceptance criteria
- [x] AC1 A workflow file `.github/workflows/ci.yml` exists and is valid YAML.
- [x] AC2 It triggers on `push` to any branch and on `pull_request` targeting `develop` and `main`.
- [x] AC3 It defines a job named `lint` that installs `requirements-dev.txt` and runs `ruff check .` and `ruff format --check .`.
- [x] AC4 It defines a job named `test` that installs `requirements-dev.txt` and runs `python src/manage.py test src`.
- [x] AC5 Both jobs set up the Python version from `.python-version`, not a hardcoded version.
- [x] AC6 The `test` job gets a `DJANGO_SECRET_KEY` generated freshly in each run. The workflow contains no key literal and references no repository secret for it.
- [x] AC7 `bash scripts/board.sh protect` requires the status checks `lint` and `test` on both `main` and `develop`. The other protection settings stay as they are.
- [ ] AC8 On this ticket's own PR, `gh pr checks` reports `lint` and `test`, both passing.

## Out of scope
- Building the Docker image in CI (#24).
- Deployments, coverage reports, caching tuning beyond pip's built-in cache, matrix builds over several Python versions.
- Requiring branches to be up to date before merging (`strict` status checks).
- Changing `enforce_admins` or review requirements in branch protection.

## Notes
- Interview answers:
  - Triggers are push to any branch plus PRs into `develop`/`main`. PR branches run twice, which is accepted.
  - CI becomes a required check on `main` and `develop`.
  - Lint and test are two separate jobs named `lint` and `test`.
  - `DJANGO_SECRET_KEY` is generated per run.
- Context:
  - There is no `.github/` yet.
  - `board.sh protect` currently sets `required_status_checks: null` on both branches. It does a full PUT, so it is safe to rerun. Rerun it once after this ticket lands on `main`, because the required checks only apply after that rerun.
  - The Python pin is `.python-version` = `3.14`.
  - The only required env var is `DJANGO_SECRET_KEY`. SQLite needs no service.
- `factory-manager` already gates on `gh pr checks` (pending → wait, failing → park). It only sees checks if the workflow runs on PRs into both `develop` and `main`.
- The assignment (`instructions/challenge.md`) asks for "a CI workflow that installs dependencies and runs the framework's test runner on every push".
- AC8 is verified by the PR's own CI run, not by a unit test. AC1 to AC7 are checked against the workflow file and the `board.sh` payload.

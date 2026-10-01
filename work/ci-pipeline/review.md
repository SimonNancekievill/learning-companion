# Review: ci-pipeline
## Verdict: PASS

There are no high-severity findings. AC1–AC7 are covered by passing tests. AC8 is enforced at delivery by the `gh pr checks` gate, as the approved plan says. The suite (21 tests) and `ruff check` / `ruff format --check` are green.

The medium findings are CI hardening and are recommended as a follow-up ticket. Both reviewers flagged the missing `permissions:` block.

## Acceptance criteria
Tests are in `config.tests.test_ci`.

- AC1 — covered by `WorkflowFileTests.test_workflow_is_a_yaml_mapping_with_jobs` — PASS
- AC2 — covered by `WorkflowFileTests.test_runs_on_every_push_and_on_pull_requests_into_develop_and_main` — PASS
- AC3 — covered by `LintJobTests.test_lint_job_installs_dev_requirements_and_runs_ruff` — PASS
- AC4 — covered by `TestJobTests.test_test_job_installs_dev_requirements_and_runs_django_tests` — PASS
- AC5 — covered by `PythonSetupTests.test_jobs_take_python_version_from_file_and_cache_pip` — PASS
- AC6 — covered by `SecretKeyTests.test_test_job_generates_a_masked_secret_key_before_running_tests` and `SecretKeyTests.test_workflow_sets_no_secret_key_literal_and_uses_no_repository_secret` — PASS. The generation step was also run locally: it writes a 67-char key and emits the mask line.
- AC7 — covered by `BranchProtectionTests.test_protect_requires_lint_and_test_on_main_and_develop` — PASS
- AC8 — verified at delivery. `factory-manager` merges the ticket PR only when `gh pr checks` reports `lint` and `test` green. It parks the ticket on failure, and a red run goes back through `tdd-implement`. — PENDING (delivery gate)

## Findings
- [medium] `.github/workflows/ci.yml:1` — There is no `permissions:` block. On `push`, the `GITHUB_TOKEN` has the repo's default scope while third-party packages install and run. Found by both reviewers. — Recommendation: add a top-level `permissions: contents: read`.
- [medium] `scripts/board.sh:193` — With required checks on `develop`, the `chore(release): merge main into develop` push from `factory-manager` (which has no CI status yet) only succeeds through the admin bypass (`enforce_admins: false`). Any admin push skips the gate. A non-admin token would get GH006. — Recommendation: document the dependency on the admin bypass. Consider routing the merge-back through a PR in a later ticket. Changing `enforce_admins` was out of scope here.
- [medium] `src/config/tests/test_ci.py:99` — `next(...)` without a default raises `StopIteration` (an error, not a failure) if the test step disappears. — Recommendation: `next(..., None)` + `assertIsNotNone` with a message.
- [low] `.github/workflows/ci.yml:12,13,30,31` — Actions are pinned to movable major tags. — Recommendation: pin to commit SHAs with a version comment, plus Dependabot for `github-actions`. The `setup-python@v7` assertion in `test_ci.py` would need adjusting.
- [low] `.github/workflows/ci.yml:12,30` — `actions/checkout` persists the token in `.git/config`. — Recommendation: `persist-credentials: false`.
- [low] `scripts/board.sh:184,196` — Required checks have no `app_id`, so any status with the context `lint`/`test` satisfies them. — Recommendation: `"app_id": 15368` (GitHub Actions), and update `REQUIRED_CHECKS`.
- [low] `scripts/board.sh:184,196` — With `strict: false`, a PR can merge without being tested against the current base. This was explicitly out of scope. — Recommendation: reconsider for `main`.
- [low] `scripts/board.sh:197` — `develop` requires no PR and has `enforce_admins: false`. This is unchanged from before. — Recommendation: see the merge-back finding above.
- [low] `src/config/tests/test_ci.py:153` — The protect test passes the full `os.environ`. Only the `PATH` shadowing stops a logged-in real `gh` from receiving PUTs. — Recommendation: fail closed with `GH_TOKEN=invalid`, `GH_HOST=invalid.localhost` and `GH_CONFIG_DIR=<tmp>`, or a minimal env.
- [low] `src/config/tests/test_ci.py:157` — With `check=True`, stderr is hidden on failure. — Recommendation: assert on `returncode` with `stderr` as the message.
- [low] `src/config/tests/test_ci.py:59` — Nothing asserts that either job checks out the repo. — Recommendation: assert one `actions/checkout@` step per job.
- [low] `.github/workflows/ci.yml:4` — An unfiltered `push:` also fires on tag pushes. — Recommendation: accept, or `branches: ["**"]`.
- [low] `requirements-dev.txt` — Pins have no hashes. — Recommendation: optionally use `--require-hashes` with a compiled lock.
- [info] After landing on `main`, run `bash scripts/board.sh protect` once so the required checks take effect.

## Reviewed
commit 37e2fcb, 2026-10-01 — reviewers: code-reviewer, security-reviewer

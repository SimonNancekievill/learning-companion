# Review: env-settings
## Verdict: PASS

No high-severity findings, every acceptance criterion is covered by a passing test, and the suite
(12 tests) plus `ruff check` / `ruff format --check` are green. The medium findings all concern the
local workflow hook `guard-bash.sh` (tooling, not the app) and are recommended as a follow-up ticket.

## Acceptance criteria
Test names below are methods in `config.tests.test_settings`.

- AC1 — covered by `SecretKeyTests.test_secret_key_is_read_from_process_environment` — PASS
- AC2 — covered by `SecretKeyTests.test_missing_secret_key_raises_improperly_configured` — PASS
- AC3 — covered by `DebugTests.test_debug_follows_django_debug_and_defaults_to_false` — PASS
- AC4 — covered by `AllowedHostsTests.test_allowed_hosts_is_comma_separated_list_and_defaults_to_empty` — PASS
- AC5 — covered by `SecretKeyTests.test_secret_key_is_read_from_dotenv_file` — PASS
- AC6 — covered by `SecretKeyTests.test_process_environment_takes_precedence_over_dotenv` — PASS
- AC7 — covered by `SecretKeyTests.test_settings_load_without_a_dotenv_file` — PASS
- AC8 — covered by `SecretKeyTests.test_settings_source_contains_no_hardcoded_secret_key` — PASS
- AC9 — covered by `RequirementsTests.test_django_environ_is_pinned_to_an_exact_version` — PASS
- AC10 — covered by `EnvExampleTests` (all three tests) — PASS

## Findings
- [medium] `.claude/hooks/guard-bash.sh:23` — The `--no-verify` check introduced in 0aca1a7 cuts at the first `;`, `&` or `|`, even inside quotes. So `git commit -m "a; b" --no-verify` and the `-m "$(cat <<EOF ...)"` form both pass the check. Found by both reviewers. — Recommendation: when `is_git commit` matches, check the whole command for `(^|\s)(--no-v[a-z-]*|-[a-zA-Z]*n[a-zA-Z]*)(\s|$)` after stripping quoted strings and heredoc bodies, or tokenise with `shlex`. Add hook self-tests.
- [medium] `.claude/hooks/guard-bash.sh:24` — Abbreviated long options (`--no-veri`) are not blocked. This predates the branch. — Recommendation: match `--no-v[a-z-]*`.
- [medium] `.claude/hooks/guard-bash.sh:14` — `is_git` misses these forms, so they skip every commit and push gate:
  - `git -c …` / `git -C …` before the subcommand
  - an env-assignment prefix, `env git` or `command git`
  - an absolute path such as `/usr/bin/git`
  - `bash -c '…'` and subshells

  This predates the branch, and no git hooks are installed (`.git/hooks` holds only samples), so this guard is the only gate. — Recommendation: allow global options and an optional prefix before the subcommand, and block `core.hooksPath` overrides.
- [low] `.claude/hooks/guard-bash.sh:45` — The force-push check misses `+refspec` pushes (`git push origin +main:main`). GitHub branch protection mitigates this. — Recommendation: also match `(\s|:)\+\S*(main|master|develop)`.
- [low] `.claude/hooks/config.sh:13` — `develop` is now in `PROTECTED_BRANCHES`, so any `git commit` on `develop` is blocked. The promotion step only uses `git merge --no-ff -m`, which the guard doesn't see as a commit. A conflicted merge is handed to a human, as `git.md` requires. — Recommendation: none needed; keep it in mind if the promotion flow changes.
- [low] `src/config/tests/test_settings.py:105` — A variable missing from `.env.example` raises `StopIteration` (an ERROR, not a FAIL). Index 0 would wrap to the last line. — Recommendation: `next(..., None)` + `assertIsNotNone`, plus `assertGreater(index, 0)`.
- [low] `src/config/tests/test_settings.py:61` — The AC7 test follows the same code path as the AC1 test. — Recommendation: also assert that `DEBUG` and `ALLOWED_HOSTS` fall back to their defaults without a `.env`.
- [low] `src/config/tests/test_settings.py:16` — `load_settings` copies only `settings.py`. A future split into several settings modules would cause an ImportError. — Recommendation: copy the `config/` package if settings are ever split.
- [low] `.env.example:8,11` — A plain `cp` gives `DJANGO_SECRET_KEY=change-me` and `DJANGO_DEBUG=True`. These are local-dev conveniences, documented as such. — Recommendation: reconsider in the Docker/deploy ticket (#23). Run `manage.py check --deploy` there, and consider rejecting weak keys.
- [low] `.gitignore:17` — Only `.env` is ignored. `.env.local` / `.env.prod` would be committed. — Recommendation: add `.env.*` and `!.env.example`.
- [low] Old `django-insecure-` key in `develop` history — harmless, because it was only ever a local dev key and settings never fall back to it. — Recommendation: no history rewrite. Never reuse that value in any environment.
- [info] CI ticket #2 must provide `DJANGO_SECRET_KEY` (e.g. generated per run). Otherwise `manage.py test` cannot load settings.

## Reviewed
commit 3080abf, 2026-10-01 — reviewers: code-reviewer, security-reviewer

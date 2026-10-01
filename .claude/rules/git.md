# Git conventions

The commit vocabulary is defined in `.conventionalcommit.json` (types, scopes, footers) and `.conventionalcommit.coauthors` (pairing trailers). This file summarises how the workflow uses them.

## Branches (gitflow)

```
feature/<id> ──squash PR──► develop ──merge-commit PR──► main
fix/<id>     ──squash PR──┘    ▲                          │
                               └── merge main into develop ┘  (before every promotion)
```

- `main` is protected (GitHub branch protection): it only receives pull requests from `develop`. Never commit or push to `main` directly.
- `develop` is the integration branch. It receives squash-merged ticket PRs and the `merge main into develop` commit before a promotion — nothing else. Never commit ticket work on it directly.
- Ticket work happens on `feature/<ticket-id>` (new behaviour) or `fix/<ticket-id>` (bugfix), created from an up-to-date `develop` by the `refine-ticket` skill.
- A ticket branch is merged into `develop` only when the ticket is fully implemented and tested: final review PASS, CI green. It is **squash-merged** via its PR (`gh pr merge --squash --delete-branch`), so every ticket lands on `develop` as one commit titled with the PR title.
- **Promotion to `main`** (owned by `factory-manager`, right after the squash merge):
  1. Resolve divergence first: `git merge --no-ff origin/main -m "chore(release): merge main into develop"` on `develop`, then push `develop`. If the merge conflicts, stop and hand the conflict to the user; never resolve semantic conflicts silently.
  2. Open a PR `develop` → `main` titled `chore(release): promote <ticket-id> to main`, body listing the ticket and `Closes #<issue>`.
  3. Merge it with a **merge commit** (`gh pr merge --merge`), never squash or rebase — `develop` and `main` must keep a shared history.
- Only when the ticket has landed on `main` does `factory-manager` mark it Done and start the next ticket.

## Commit messages

Conventional Commits, `<type>(<scope>): <subject>`, with the types and scopes from `.conventionalcommit.json`:

- Scope is the ticket id on ticket branches, `repo` for root configuration, tooling and workflow setup outside a ticket, `release` for promoting `develop` to `main` (the main → develop merge commit and the release PR).
- `feat(<ticket-id>): <what the step delivers>` for a plan step on a `feature/` branch, `fix(<ticket-id>): ...` for a plan step on a `fix/` branch.
- `refactor(<ticket-id>): ...` for pure refactoring on green, `test(<ticket-id>): ...` for adding or correcting tests on their own.
- `docs(<ticket-id>): ...` for workflow artifacts (ticket, plan, review) and documentation.
- `chore`, `build`, `ci`, `revert` as described in `.conventionalcommit.json`.
- Footers: `BREAKING CHANGE:`, `Closes #<n>`, and `Co-authored-by:` lines copied from `.conventionalcommit.coauthors`, after a blank line at the end of the message.
- PR titles follow the same format, because they become the squash and merge commit subjects: `feat(<id>): <ticket title>` (or `fix(<id>): ...`) for a ticket PR, `chore(release): promote <id> to main` for a release PR.

## Rules

- Commit after every green TDD cycle. Small commits are the audit trail of the workflow; do not batch several steps into one commit.
- Commits require a green test suite and `--no-verify` is forbidden (both enforced by a hook).
- Pushing is only possible once the final review has passed (phase `done`, enforced by a hook).
- A PR is merged only when its CI checks are green (`gh pr checks`). If no checks are reported yet (before the CI ticket lands), the review verdict is the gate.
- Never rewrite history on `main` or `develop`, never force-push them, never delete them.

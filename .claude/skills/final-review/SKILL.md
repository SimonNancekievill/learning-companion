---
name: final-review
description: Run the final quality gate - independent code and security review agents plus an acceptance-criteria check - and on PASS unlock push and open the PR. Last phase of the development workflow. Use after tdd-implement, when the phase is reviewing.
---

# Final review

## Preconditions

Read `.claude/state/workflow.json`. The phase must be `reviewing`. All plan steps in `work/<id>/plan.md` must be ticked. If not, stop and point the user back to `tdd-implement`.

## Steps

1. Collect the diff under review: `git diff develop...HEAD` (paths only in the main context; the reviewers read the contents themselves).
2. **Verification fan-out.** Spawn both reviewers in parallel, each with its own lens and a clean context:
   - `code-reviewer` agent: correctness, plan conformance, test quality of the changed files.
   - `security-reviewer` agent: OWASP Top 10, authn/authz, secrets in the changed files.

   The reviewers are read-only by design. They report findings; they do not fix anything.
3. **Acceptance check** (main session): for each acceptance criterion in `work/<id>/ticket.md`, name the test that proves it and confirm the test passes. Run the full suite and lint once more.
4. Write `work/<id>/review.md`:

   ```markdown
   # Review: <id>
   ## Verdict: PASS | FAIL
   ## Acceptance criteria
   - AC1 — covered by `<test>` — PASS
   ## Findings
   - [severity] file:line — description — recommendation
   ## Reviewed
   commit <sha>, <date>
   ```

   Verdict rules: any high-severity finding, any uncovered acceptance criterion, or a red suite means FAIL. Do not soften a FAIL into a PASS-with-remarks.

## On FAIL

Append the findings as new unchecked steps to `work/<id>/plan.md`, then:

```bash
bash .claude/hooks/set-state.sh phase implementing
bash scripts/board.sh status <issue> "In progress"    # <issue> from .claude/state/workflow.json
git add work/<id> work/backlog.md && git commit -m "docs(<id>): review findings"
```

Tell the user to rerun `tdd-implement` for the new steps. Do not fix findings inside the review.

## On PASS

```bash
bash .claude/hooks/set-state.sh phase done
git add work/<id> && git commit -m "docs(<id>): review passed"
git push -u origin "$(git branch --show-current)"    # feature/<id> or fix/<id>
gh pr create --base develop --title "feat(<id>): <title>" --body "<story, acceptance criteria, reference to work/<id>/review.md, Refs #<issue>>"
```

Use `fix(<id>): <title>` as the PR title on a `fix/` branch. The PR title becomes the squash commit on `develop`, so it must be a valid Conventional Commit subject. Write `Refs #<issue>`, not `Closes` — the issue is closed by the release PR into `main`.

The board stays at In review: the ticket is not delivered until `factory-manager` has squash-merged the PR into `develop` and promoted it to `main`. Do not merge the PR yourself.

Report the PR URL to the user. The push gate only opens in phase `done`, so a push that gets blocked means the state transition did not happen — check, don't force.

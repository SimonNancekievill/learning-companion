---
name: factory-manager
description: Inspects the ticket backlog, the GitHub project board and the current workflow phase, then triggers the one pipeline skill (refine-ticket, plan-ticket, tdd-implement, or final-review) that owns the next step, or delivers a reviewed ticket (squash-merge into develop, promote develop to main). Picks the next queued ticket once the previous one is on main. Advances the pipeline by exactly one step per call and reports cleanly, so it is safe to invoke repeatedly, including from a loop. Use when the user wants the AI factory to keep moving without manually tracking phase and ticket state themselves.
---

# Manage the AI factory

Orchestrates the pipeline defined in `.claude/rules/workflow.md`. This skill never changes `phase` itself, never writes source code, and never invokes more than one phase skill per call — it only reads state, decides which phase skill owns the next step, and triggers it with the `Skill` tool. All actual work and every phase transition still happens inside `refine-ticket`, `plan-ticket`, `tdd-implement`, and `final-review`.

## Preconditions

1. Read `.claude/state/workflow.json`. It may not exist yet — treat a missing file or a missing `phase` key as phase `idle`, exactly like `lib.sh:current_phase` does. Note `ticket` and `issue` the same way (missing = none).
2. Read `work/backlog.md`. If it doesn't exist, create it with just this header, then stop this call and report that the backlog is empty and needs entries:

   ```markdown
   # Ticket backlog

   Queue for `factory-manager`, kept in sync with the GitHub issues and project board by
   `scripts/board.sh`. One ticket per line, top to bottom = priority order. Add new ideas
   as plain `- [ ] <title>: <description>` lines (or as issues on the board); the issue
   number, status and ticket id are filled in by the pipeline — leave them alone.
   ```
3. `work/board.json` must exist (it holds the project board ids). If it doesn't, stop and tell the user to run `bash scripts/board.sh setup` once.

## Steps

Do exactly one of the following, then stop and report (step 6). Never chain two phase skills in one call — one call is one observable pipeline step.

1. **Idempotence check.** If `ticket` is set, find its line in `work/backlog.md`. If that line carries `[[parked: <skill> @ <phase>]]` and `<phase>` equals the *current* phase, the last call already triggered `<skill>` at this phase and it stopped to ask a human something, and nothing has moved since. Do not re-invoke it — go straight to step 6 and report that it is still waiting. Otherwise (no tag, or the tag's phase no longer matches — meaning progress happened since) continue normally and discard any stale tag when you next touch that line.

2. **Dispatch on phase:**

   | phase | action |
   |---|---|
   | `idle` | Sync + selection (steps 3 and 5). |
   | `done` | Delivery (step 4); once the ticket is on `main`, close-out, sync + selection. |
   | `refined` | Invoke `plan-ticket`. |
   | `planned` | Invoke `tdd-implement`. |
   | `implementing` | Invoke `tdd-implement` (it resumes from the plan itself). |
   | `reviewing` | Invoke `final-review`. |

3. **Sync.** Run `bash scripts/board.sh sync`. It turns new `- [ ] <title>: <description>` backlog lines into issues on the board, imports Todo issues that were added on the board directly, and prints `drift:` lines where board and backlog disagree. Do not fix drift by guessing — include it in the report and let the user decide which side is right.

4. **`done` — delivery.** The ticket goes `feature/<id>` (or `fix/<id>`) → `develop` → `main` following `.claude/rules/git.md`. Work out where it is with `gh pr list --state all --head <branch> --json number,state,title` for the ticket PR and `gh pr list --state all --base main --head develop --json number,state,title` for the release PR whose title names `<id>`, then do the **first** row that applies and stop:

   | state | action |
   |---|---|
   | Ticket PR open | Check CI with `gh pr checks <pr>`. Pending → report "waiting for CI" and stop. Failing → report the failing checks, tag the line `[[parked: ci-failed @ done]]` and stop; a fix goes back through `tdd-implement`, not through this skill. No checks reported, or all green → make sure the working tree is clean, then `gh pr merge <pr> --squash --delete-branch --subject "<PR title> (#<pr>)" --body "Refs #<issue>"`, then `git switch develop && git pull --ff-only` and `bash scripts/board.sh status <issue> "In develop"`. |
   | Ticket PR merged, no release PR for `<id>` | Promote: `git switch develop && git pull --ff-only && git fetch origin`, then `git merge --no-ff origin/main -m "chore(release): merge main into develop"`. On a conflict: `git merge --abort`, tag the line `[[parked: release-conflict @ done]]`, report the conflicting files and stop — a human resolves it. Otherwise `git push origin develop` and `gh pr create --base main --head develop --title "chore(release): promote <id> to main" --body "<ticket title, link to work/<id>/review.md>\n\nCloses #<issue>"`. |
   | Release PR open | Check CI exactly as for the ticket PR (same pending/failing handling). Green → `gh pr merge <pr> --merge --subject "chore(release): promote <id> to main (#<pr>)" --body "Closes #<issue>"`. Never squash or rebase a release PR. |
   | Release PR merged | The ticket is on `main`: close-out, then continue with sync (step 3) and selection (step 5) in this same call. |

   `work/backlog.md` changes made during delivery stay uncommitted (commits on `develop` are not allowed); stash them with `git stash push -- work/backlog.md` before any `git switch`, `pull` or `merge` and `git stash pop` right after. The next ticket's `refine-ticket` commit picks them up.

   **Close-out:** if the issue is still open, `gh issue close <issue> --comment "Released to main"`. Run `bash scripts/board.sh status <issue> "Done"` and append ` — work/<id>/review.md` to the ticket's backlog line. Run `git status`; anything other than the backlog change means something is off — stop and report it. `git switch develop && git pull --ff-only` so the next ticket branches off the released state.

5. **Selection.** Read the backlog top to bottom and pick the first `- [ ] #<n> (Todo)` line, skipping any whose description names a dependency that's still open (e.g. "after X ships") — log a skip like that rather than guessing an order, and ask the user only if two candidates are genuinely ambiguous in priority. If no eligible line exists, report **"Backlog is empty — nothing to do"** and stop; that's the signal for a wrapping loop to stop too.

   Invoke `refine-ticket` with `#<n> <description>` as its argument; it creates the branch, records `issue <n>`, and moves the ticket to Refined on the board and in the backlog. Afterwards, re-read `.claude/state/workflow.json`:
   - If `phase` is now `refined`, the line has been updated by `refine-ticket` — nothing more to do.
   - If `phase` is still `idle`/unchanged, `refine-ticket` stopped mid-interview (or asked for ticket-id confirmation) — leave the line as is but add `[[parked: refine-ticket @ idle]]` so the next call doesn't restart the interview from scratch.

6. **Report.** One short summary: phase before → phase after, the ticket id and issue, board status before → after, and the artifact, PR or merge that changed. Include any `drift:` lines from the sync. If the invoked skill stopped to ask the user something — ticket interview, ticket-id confirmation, plan approval — say exactly that instead of answering on its behalf; a human needs to be present for that turn, and this skill does not fabricate approval to keep a loop moving.

## Hard limits

- Never call `.claude/hooks/set-state.sh`; only the phase skill that owns a transition may change `phase`, `ticket` or `issue`.
- Never invoke more than one phase skill per call, and never do more than one delivery row per call (except continuing from close-out into sync + selection).
- Never fabricate or infer the user's approval of a ticket or plan.
- Never write source code from this skill (the write-protection hook would block it outside `implementing` anyway); it only ever delegates.
- Never merge a PR with failing CI, never squash a release PR, never push to `main`, never force-push, never resolve a merge conflict yourself.
- Change a ticket's status only with `bash scripts/board.sh status`, so board and backlog never diverge. Never reorder or delete backlog lines beyond what `board.sh` and the `[[parked: ...]]` tag do.
- Don't try to commit backlog edits made while `phase` is `idle` or during delivery — `guard-bash.sh` blocks commits in `idle` and `develop` takes no direct commits; leave the edit uncommitted, the next phase skill's own commit picks it up.

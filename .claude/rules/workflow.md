# Development workflow

All feature work in this project follows a fixed pipeline. Each phase is a skill, each phase produces an artifact in `work/<ticket-id>/`, and hooks enforce the gates. The current phase lives in `.claude/state/workflow.json` and is injected into every prompt.

| Phase          | Skill            | Artifact                    | Exit condition                                  | Board status  |
|----------------|------------------|-----------------------------|--------------------------------------------------|---------------|
| `idle`         | `factory-manager`| backlog line + issue        | Next ticket picked                               | Todo          |
| `refined`      | `refine-ticket`  | `work/<id>/ticket.md`       | User approves acceptance criteria                | Refined       |
| `planned`      | `plan-ticket`    | `work/<id>/plan.md`         | User approves the plan                           | Planned       |
| `implementing` | `tdd-implement`  | green commits, ticked plan  | All plan steps done, suite green                 | In progress   |
| `reviewing`    | `final-review`   | `work/<id>/review.md`       | Verdict PASS, ticket PR open against `develop`   | In review     |
| `done`         | `factory-manager`| squash merge, release PR    | Ticket squash-merged into `develop` ...          | In develop    |
|                |                  |                             | ... and promoted to `main`                       | Done          |

Delivery after `done` follows the gitflow in `.claude/rules/git.md`: `factory-manager` squash-merges the ticket PR into `develop`, merges `main` back into `develop`, and merges a release PR into `main`. The next ticket starts only after the current one has landed on `main`.

Rules that always apply:

- Never skip a phase and never set the phase yourself outside of the skill that owns the transition. Phases are changed only via `bash .claude/hooks/set-state.sh`, exactly where a skill says so.
- Source code is write-protected outside the `implementing` phase (enforced by a hook). If a write is blocked, do not work around it — you are in the wrong phase.
- Each phase works from the previous phase's artifact, not from the conversation. If `plan.md` is missing context, fix `plan.md`, don't improvise.
- Review findings are not fixed during review. They become new steps in `plan.md` and go back through `tdd-implement`.
- Tickets are tracked in three places that must never disagree: the line in `work/backlog.md`, the GitHub issue, and its card on the GitHub project board. Every status change goes through `bash scripts/board.sh status <issue> "<status>"`, which updates the board and the backlog line together, at the point the table above names. Never edit a status marker by hand and never move a card on the board without the script. The issue number lives in the state file as `issue`.
- If the user asks for a quick change outside the workflow (typo, config tweak, docs), say so explicitly and ask whether to bypass the workflow for it; markdown and config files are not write-protected.

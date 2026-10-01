# Learning Companion

Track learning goals and sessions, attach reference material, and get AI-powered progress summaries and next steps. Built with Django as Recap Project 6 (Agentic Engineering & AI Factory), see `instructions/`.

## Getting started

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
cp .env.example .env
.venv/bin/python src/manage.py migrate
.venv/bin/python src/manage.py runserver
```

Run the tests with `.venv/bin/python src/manage.py test src` and the linter with `.venv/bin/ruff check .`.

## How it is built

Features are delivered one ticket at a time by a Claude Code pipeline: refine ticket → plan → TDD implementation → independent review → squash-merged PR into `develop` → release PR into `main`. The next ticket starts once the previous one is on `main`.

The queue is `work/backlog.md`, mirrored as GitHub issues on the project board by `scripts/board.sh`; each ticket's artifacts live in `work/<ticket-id>/`. The pipeline itself is documented in `docs/ai-factory-workflow.md`, the gitflow in `.claude/rules/git.md`.

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

import yaml
from django.test import SimpleTestCase

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_FILE = REPO_ROOT / ".github" / "workflows" / "ci.yml"


def workflow() -> dict:
    # YAML 1.1 parses the unquoted `on:` key as boolean True.
    return yaml.safe_load(WORKFLOW_FILE.read_text())


class DevRequirementsTests(SimpleTestCase):
    def test_pyyaml_is_pinned_to_an_exact_version(self):
        requirements = (REPO_ROOT / "requirements-dev.txt").read_text()

        self.assertRegex(requirements, re.compile(r"^PyYAML==\d+\.\d+\.\d+$", re.M))


class WorkflowFileTests(SimpleTestCase):
    def test_workflow_is_a_yaml_mapping_with_jobs(self):
        self.assertTrue(WORKFLOW_FILE.is_file(), f"{WORKFLOW_FILE} is missing")
        data = workflow()

        self.assertIsInstance(data, dict)
        self.assertIsInstance(data.get("jobs"), dict)

    def test_runs_on_every_push_and_on_pull_requests_into_develop_and_main(self):
        data = workflow()
        self.assertIn(True, data, "workflow has no `on:` triggers")
        triggers = data[True]

        self.assertIn("push", triggers)
        self.assertNotIn("branches", triggers["push"] or {})
        self.assertEqual(set(triggers["pull_request"]["branches"]), {"develop", "main"})


class JobTestCase(SimpleTestCase):
    def job(self, name: str) -> dict:
        jobs = workflow()["jobs"]
        self.assertIn(name, jobs, f"workflow has no `{name}` job")
        return jobs[name]

    def steps(self, name: str) -> list[dict]:
        return self.job(name).get("steps", [])

    def run_script(self, name: str) -> str:
        """All `run:` commands of the job, joined in step order."""
        return "\n".join(step["run"] for step in self.steps(name) if "run" in step)


class LintJobTests(JobTestCase):
    def test_lint_job_installs_dev_requirements_and_runs_ruff(self):
        self.assertEqual(self.job("lint")["runs-on"], "ubuntu-latest")
        script = self.run_script("lint")

        self.assertIn("pip install -r requirements-dev.txt", script)
        self.assertIn("ruff check .", script)
        self.assertIn("ruff format --check .", script)


class TestJobTests(JobTestCase):
    def test_test_job_installs_dev_requirements_and_runs_django_tests(self):
        self.assertEqual(self.job("test")["runs-on"], "ubuntu-latest")
        script = self.run_script("test")

        self.assertIn("pip install -r requirements-dev.txt", script)
        self.assertIn("python src/manage.py test src", script)


class PythonSetupTests(JobTestCase):
    def test_jobs_take_python_version_from_file_and_cache_pip(self):
        for name in ("lint", "test"):
            with self.subTest(job=name):
                setup = [
                    step
                    for step in self.steps(name)
                    if step.get("uses", "").startswith("actions/setup-python@")
                ]
                self.assertEqual(len(setup), 1, "expected exactly one setup-python step")
                self.assertEqual(setup[0]["uses"], "actions/setup-python@v7")
                options = setup[0].get("with", {})

                self.assertEqual(options.get("python-version-file"), ".python-version")
                self.assertNotIn("python-version", options)
                self.assertEqual(options.get("cache"), "pip")
                self.assertIn("requirements-dev.txt", options.get("cache-dependency-path", ""))


class SecretKeyTests(JobTestCase):
    def test_test_job_generates_a_masked_secret_key_before_running_tests(self):
        runs = [step.get("run", "") for step in self.steps("test")]
        test_index = next(i for i, run in enumerate(runs) if "manage.py test" in run)
        generators = [
            run
            for run in runs[:test_index]
            if "secrets.token_urlsafe" in run and "DJANGO_SECRET_KEY=" in run
        ]

        self.assertEqual(len(generators), 1, "no step generates DJANGO_SECRET_KEY before tests")
        self.assertIn("::add-mask::", generators[0])
        self.assertIn('>> "$GITHUB_ENV"', generators[0])

    def test_workflow_sets_no_secret_key_literal_and_uses_no_repository_secret(self):
        data = workflow()
        envs = [data.get("env", {})]
        for job in data["jobs"].values():
            envs.append(job.get("env", {}))
            envs.extend(step.get("env", {}) for step in job.get("steps", []))

        for env in envs:
            self.assertNotIn("DJANGO_SECRET_KEY", env)
        self.assertNotRegex(WORKFLOW_FILE.read_text(), r"\$\{\{\s*secrets\.")


FAKE_GH = """#!/usr/bin/env bash
# Stand-in for the GitHub CLI: answers `repo view`, records every `api` call.
if [ "$1" = repo ] && [ "$2" = view ]; then
  case "$*" in
    *"--json owner"*) echo acme ;;
    *"--json name"*) echo proj ;;
  esac
  exit 0
fi
if [ "$1" = api ]; then
  i="$(ls "$FAKE_GH_LOG" | grep -c '[.]args$')"
  printf '%s\\n' "$@" > "$FAKE_GH_LOG/$i.args"
  cat > "$FAKE_GH_LOG/$i.json"
fi
exit 0
"""

REQUIRED_CHECKS = {"strict": False, "checks": [{"context": "lint"}, {"context": "test"}]}


class BranchProtectionTests(SimpleTestCase):
    def protect_calls(self) -> list[tuple[list[str], dict]]:
        """Run `board.sh protect` against a fake gh; return each api call's (argv, payload)."""
        with tempfile.TemporaryDirectory() as tmp:
            bin_dir, log_dir = Path(tmp, "bin"), Path(tmp, "log")
            bin_dir.mkdir()
            log_dir.mkdir()
            fake_gh = bin_dir / "gh"
            fake_gh.write_text(FAKE_GH)
            fake_gh.chmod(0o755)
            env = os.environ | {
                "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
                "FAKE_GH_LOG": str(log_dir),
            }
            subprocess.run(
                ["bash", "scripts/board.sh", "protect"],
                cwd=REPO_ROOT,
                env=env,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                check=True,
                timeout=30,
            )
            return [
                (args.read_text().splitlines(), json.loads(args.with_suffix(".json").read_text()))
                for args in sorted(log_dir.glob("*.args"))
            ]

    def test_protect_requires_lint_and_test_on_main_and_develop(self):
        calls = self.protect_calls()

        paths = [next(arg for arg in argv if arg.startswith("repos/")) for argv, _ in calls]
        self.assertEqual(
            paths,
            [
                "repos/acme/proj/branches/main/protection",
                "repos/acme/proj/branches/develop/protection",
            ],
        )
        main, develop = (payload for _, payload in calls)
        self.assertEqual(
            main,
            {
                "required_status_checks": REQUIRED_CHECKS,
                "enforce_admins": True,
                "required_pull_request_reviews": {"required_approving_review_count": 0},
                "restrictions": None,
                "allow_force_pushes": False,
                "allow_deletions": False,
            },
        )
        self.assertEqual(
            develop,
            {
                "required_status_checks": REQUIRED_CHECKS,
                "enforce_admins": False,
                "required_pull_request_reviews": None,
                "restrictions": None,
                "allow_force_pushes": False,
                "allow_deletions": False,
            },
        )

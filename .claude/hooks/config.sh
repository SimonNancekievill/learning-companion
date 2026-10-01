# Project-specific configuration for the workflow hooks.
# Adapt these to your project. Everything else should work unchanged.

TEST_CMD="npm test --silent"
LINT_CMD="npm run lint --silent"

# Run the test suite after every source/test file write (records red/green
# for the TDD cycle). Set to "false" if your suite is too slow for that;
# tests are then only enforced at commit time.
RUN_TESTS_ON_WRITE="true"

# Branches that may never receive direct commits or force-pushes.
PROTECTED_BRANCHES="main|master"

# Directories that count as production/test code (used by the write guard).
SOURCE_DIRS="src|app|lib|test|tests|__tests__"

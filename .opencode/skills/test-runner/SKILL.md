---
name: test-runner
description: Executes tests, analyzes coverage, and debugs test failures in Python repositories using pytest.
---

## What I do

- Run the pytest suite (all tests or targeted files/tests)
- Generate and analyze code coverage reports
- Help debug failing tests and explain error outputs
- Advise on common pytest fixtures and test setup patterns
- Assess code quality using coverage and test output

## When to use me

Use this when you need to execute tests, check coverage, or troubleshoot test failures in a Python project using pytest. This includes running all tests, single test files, specific test cases, or debugging targeted failures.

## Procedure

1. (Optional) Activate your Conda environment (for example, `conda activate pogo-team-optimizer`)
2. Run all tests: `pytest`
3. Run tests with coverage: `pytest --cov --cov-report=term-missing`
4. Generate HTML coverage report when needed: `pytest --cov --cov-report=html`
5. Run a specific test file: `pytest path/to/test_file.py`
6. Run a specific test case: `pytest path/to/test_file.py::test_name`
7. Debug failures by reviewing pytest tracebacks, assertion diffs, and fixture setup
8. Fix code or tests based on issues identified by pytest outputs

## Related Guidelines

- Follow test naming and structure conventions in this project
- Use pytest fixtures, mocks, and setup/teardown patterns (`@pytest.fixture`, `yield`, `monkeypatch`)
- Ensure lint and pre-commit checks pass before commits
- Refer to AGENTS.md for organizational and style conventions

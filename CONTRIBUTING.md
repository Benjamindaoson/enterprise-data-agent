# Contributing

Thank you for improving **enterprise-data-agent**.

## Scope

Contributions should strengthen the implemented system, reproducibility, tests, documentation, or evidence boundaries. Roadmap ideas must be labeled as planned and must not be presented as measured results.

## Workflow

1. Open or reference an issue describing the problem and expected evidence.
2. Create a focused branch.
3. Keep secrets, private datasets, generated outputs, and large runtime artifacts out of Git.
4. Add or update tests and documentation.
5. Run the relevant checks before opening a pull request.

## Required checks

- `pytest`
- `ruff check .`
- `mypy` using the repository configuration
- relevant evaluation and Docker checks for changed runtime paths

## Pull-request evidence

Include:

- what changed and why;
- commands executed and observed results;
- affected contracts, data, or evaluation assumptions;
- failure and rollback considerations;
- screenshots only when they verify a user-visible change.

Do not fabricate metrics, promote simulated behavior as real deployment, or weaken safety and validation boundaries to make a test pass.

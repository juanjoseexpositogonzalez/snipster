# snipster
Intermediate Cohort Project

# Description
snipster is an application developed as part of the Intermediate Cohort. The project is organized to support Python development, testing, and maintenance, with dependency management, code quality tools, and automated testing.

# Project Structure
- src/
Main application source code.

- tests/
Automated tests for the code in src.

- .env and .env.example
Environment variable files for local and example configuration.

- pyproject.toml
Project dependencies and tool configuration.

- uv.lock
Dependency lock file.

- .pre-commit-config.yaml
Pre-commit hook configuration.

- .pylintrc
Pylint static analysis configuration.

- .python-version
Specifies the Python version used.

- .coverage, htmlcov/
Test coverage files and reports.

- .ruff_cache/, .pytest_cache/
Linting and test tool caches.

- snippets.json, snipster.db
Data and internal configuration files.

# Installation
Clone the repository:
```bash
git clone <repository-url>
cd snipster
```

Install dependencies:
```bash
pip install -e .[dev]
```

Copy the example environment file and configure your variables:
```bashbash
cp .env.example .env
```

# Usage
The main source code is in the src directory. Run the application or scripts as documented in each module.

Testing
To run automated tests:
```bash
pytest tests/
```

To view the coverage report:
```bash
pytest --cov=src --cov-report html
```

The HTML report will be in `index.html.`

Code Quality
Linting with Ruff and Pylint:
```bash
ruff src/
pylint src/
```

Pre-commit hooks:
```bash
pre-commit run --all-files
```
# Task Runner
This project uses poethepoet as a task runner. Several useful commands are defined in the [tool.poe.tasks] section of pyproject.toml:

- test:

```pytest -vv --cov=src --cov-report=term-missing --cov-report=html```

- lint:

```ruff check src```

- format:

```ruff format src```

- format-check:

```ruff check src --fix```

- type-check:
``` ruff typecheck src```

- run:
```snipster```

- tc:

```ty check .```

To run a task, use:

```bash
poe <task-name>
# Example:
poe test
```

# Contributing
Fork the repository.
Create a branch for your feature or fix.
Make your changes and ensure all tests pass.
Submit a pull request.

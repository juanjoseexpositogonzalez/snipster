📝 snipster

![Python](https://img.shields.io/badge/python-3.12+-blue.svg)
![uv](https://img.shields.io/badge/uv-managed-orange.svg)
![PostgreSQL](https://img.shields.io/badge/postgresql-optional-blue.svg)

> 🎯 Intermediate Cohort Project - A powerful snippet management tool


# 📋 Description
`snipster` is an application developed as part of the Pybites' Intermediate Cohort. The project is organized to support Python development, testing, and maintenance, with dependency management, code quality tools, and automated testing.

# 📁 Project Structure

- 📂 `src/` - Main application source code
- 🧪 `tests/` - Automated tests for the code in src
- ⚙️ `.env` and `.env.example` - Environment variable files
- 📦 `pyproject.toml` - Project dependencies and tool configuration
- 🔒 `uv.lock` - Dependency lock file
- 🎣 `.pre-commit-config.yaml` - Pre-commit hook configuration
- 📊 `.pylintrc` - Pylint static analysis configuration
- 🐍 `.python-version` - Specifies the Python version used
- 📈 `.coverage`, `htmlcov/` - Test coverage files and reports
- 🗃️ `snippets.json`, `snipster.db` - Data and internal configuration files

# ⚡ Installation

Requirements:
- 🐍 Python 3.12+
- 📦 uv
- 🐘 PostgreSQL (optional, for database support)
- 🎭 Poe the poet (for task management)

## 🚀 Clone and Install
To get started, clone the repository and install the dependencies. Make sure you have Python 3.12 or higher installed.

Clone the repository:
```bash
git clone <repository-url>
cd snipster
```

Install dependencies:
```bash
uv sync --lock
```

Copy the example environment file and configure your variables:
```bash
cp .env.example .env
```

# 🎯 Usage

## 💻 CLI

```bash
uv run snipster --help

Usage: snipster.exe [OPTIONS] COMMAND [ARGS]...

 Snipster CLI - A command-line interface for managing your snippets.


┌─ Options ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ --install-completion          Install completion for the current shell.                                                                                                                                                │
│ --show-completion             Show completion for the current shell, to copy it or customize the installation.                                                                                                         │
│ --help                        Show this message and exit.                                                                                                                                                              │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
┌─ Commands ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ add                                                                                                                                                                                                                    │
│ list                                                                                                                                                                                                                   │
│ delete                                                                                                                                                                                                                 │
│ search                                                                                                                                                                                                                 │
│ toggle-favorite                                                                                                                                                                                                        │
│ tag                                                                                                                                                                                                                    │
│ run               Run code in a specific language using Piston API.                                                                                                                                                    │
│ image                                                                                                                                                                                                                  │
│ gist              Create a Gist from a snippet.                                                                                                                                                                        │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## 🖥️ API

To run the FastAPI application, use:

```bash
uv run fastapi dev src/snipster/api.py
```

You can then access the API documentation at `http://localhost:8000/docs`.

## 📱 GUI

To run the Streamlit application, use:

```bash
streamlit run src/snipster/streamlit_app.py
```

You can then access the GUI at `http://localhost:8501`.

# 🏃‍♂️ Task Runner
This project uses poethepoet as a task runner. Several useful commands are defined:

- 🧪 **test**: `pytest -vv --cov=src --cov-report=term-missing --cov-report=html`
- 🔍 **lint**: `ruff check src`
- ✨ **format**: `ruff format src`
- 🔧 **format-check**: `ruff check src --fix`
- 📝 **type-check**: `ruff typecheck src`
- ▶️ **run**: `snipster`

To run a task, use:

```bash
poe <task-name>
# Example:
poe test
```

# Contributing
Contributions are welcome! If you have suggestions or improvements, please follow these steps:
1. Fork the repository.
2. Create a branch for your feature or fix.
3. Make your changes and ensure all tests pass.
4. Submit a pull request.

# License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details

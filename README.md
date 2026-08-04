# triagectl

`triagectl` is a lightweight Python CLI project for managing and executing automated incident triage workflows.

## Features

- **Console Script**: Global `triage` command line interface.
- **Environment Driven**: Automatic `.env` loading for configurable secrets and parameters.
- **Editable Installation**: Fully customizable and installable locally using `pip install -e .`.

## Directory Structure

```text
triagectl/
├── .env.example       # Sample environment variables template
├── pyproject.toml     # Build specification and console script configuration
├── README.md          # Project documentation
├── requirements.txt   # Runtime dependencies
└── triagectl/
    ├── __init__.py    # Package initialization and version definition
    └── cli.py         # CLI logic and subcommand handlers
```

## Installation

To install `triagectl` in editable mode:

```bash
# Clone or navigate to project directory
cd triagectl

# Install dependencies and package in editable mode
pip install -e .
```

## Environment Setup

Copy `.env.example` to `.env` to set your local parameters and secrets:

```bash
cp .env.example .env
```

Available configuration keys:
- `TRIAGE_ENV`: Target environment (e.g. `development`, `production`).
- `TRIAGE_API_URL`: API service endpoint.
- `TRIAGE_API_KEY`: Secret authentication key.
- `TRIAGE_DEBUG`: Set to `true` or `false`.

## Usage

Once installed, use the `triage` command from your terminal:

```bash
# Check version
triage --version

# View system status
triage status

# Execute triage on a target
triage run service-alpha --dry-run

# Inspect loaded configuration
triage config
```

# UV Quick Start Guide

## Installation

### Install UV
```bash
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Using UV with Push Service

### 1. Sync Dependencies
```bash
# Install all dependencies (including dev dependencies)
uv sync

# Install only production dependencies
uv sync --no-dev
```

### 2. Run Commands
```bash
# Run pytest
uv run pytest tests/unit/ -v

# Run with coverage
uv run pytest tests/unit/ --cov=app --cov-report=html

# Start the service
uv run uvicorn app.main:app --reload --port 8004

# Run alembic migrations
uv run alembic upgrade head
```

### 3. Add Dependencies
```bash
# Add a new production dependency
uv add package-name

# Add a dev dependency
uv add --dev package-name

# Add with specific version
uv add package-name==1.2.3
```

### 4. Remove Dependencies
```bash
uv remove package-name
```

### 5. Update Dependencies
```bash
# Update all dependencies
uv sync --upgrade

# Update specific package
uv add package-name --upgrade
```

### 6. Create Virtual Environment (Optional)
```bash
# UV automatically manages venvs, but you can create one manually
uv venv

# Activate it
# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

## Common Commands

| Task | Command |
|------|---------|
| Install dependencies | `uv sync` |
| Run tests | `uv run pytest tests/unit/ -v` |
| Start service | `uv run uvicorn app.main:app --reload --port 8004` |
| Add package | `uv add package-name` |
| Remove package | `uv remove package-name` |
| Update all | `uv sync --upgrade` |
| Run script | `uv run python script.py` |

## Benefits of UV

✅ **10-100x faster** than pip
✅ **Automatic virtual environment** management
✅ **Lock file** for reproducible builds
✅ **Cross-platform** consistency
✅ **Drop-in replacement** for pip
✅ **Built-in Python version** management

## Migration from requirements.txt

The project now uses `pyproject.toml` instead of `requirements.txt`:

- Dependencies are in `[project.dependencies]`
- Dev dependencies are in `[project.optional-dependencies.dev]`
- No need to manually manage virtual environments
- UV handles everything automatically

## Troubleshooting

### UV not found
```bash
# Add UV to PATH or use full path
~/.cargo/bin/uv sync
```

### Python version mismatch
```bash
# UV will use the version from .python-version (3.11)
# Install Python 3.11 if needed
uv python install 3.11
```

### Clear cache
```bash
uv cache clean
```

## Learn More

- UV Documentation: https://docs.astral.sh/uv/
- GitHub: https://github.com/astral-sh/uv

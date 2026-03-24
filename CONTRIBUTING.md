# Contributing to The Director

Thank you for your interest in contributing! This project follows a quality-first approach — every change must pass the existing test suite and maintain contract integrity.

## Getting Started

```bash
# Fork and clone
git clone https://github.com/<your-username>/the-director.git
cd the-director

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests to make sure everything works
python -m pytest tests/ -v
```

## Development Workflow

1. **Create a branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** — follow the existing code patterns

3. **Run tests** before committing:
   ```bash
   python -m pytest tests/ -v
   ```

4. **Lint your code**:
   ```bash
   ruff check src/ tests/
   ```

5. **Submit a Pull Request** with a clear description

## Rules

- **Never break existing contracts** — `models.py` is the source of truth. If you change a model, update all validators and tests.
- **Never skip validation** — Every artifact must pass Pydantic validation before it can be written.
- **Test everything** — New validators need new tests. New models need new test fixtures.
- **Keep scope boundaries** — The Director owns pre-production only. No visual design, no motion physics, no component selection.

## What We're Looking For

- 🔧 New validators for edge cases
- 📐 Additional Pydantic constraints
- 🧪 More test coverage
- 📖 Documentation improvements
- 🐛 Bug fixes with reproduction test cases

## Code Style

- Python 3.11+ with type hints everywhere
- Pydantic v2 models with `Field()` descriptions
- Descriptive error messages that tell the user what to fix
- Docstrings on all public functions and classes

## Questions?

Open an issue — we're happy to help.

# Contributing

## Development Setup

Install the package with development dependencies:

```bash
pip install -e ".[dev]"
```

`prompt.md` must be present in the working directory when running the tool or
tests that exercise `generate_new_filename` without mocking the file read.

## Testing

Run the full test suite:

```bash
pytest
```

Run with coverage:

```bash
pytest --cov=. --cov-report=term-missing
```

Tests live in `test_pdf_renamer.py` alongside the source. All Ollama HTTP calls
and filesystem operations are mocked — no running Ollama instance is required to
run the tests.

## Code Quality

Format, lint, and security-scan with the dev tools configured in `pyproject.toml`:

```bash
black pdf_renamer.py test_pdf_renamer.py
flake8 pdf_renamer.py
bandit -c pyproject.toml -r pdf_renamer.py
vulture pdf_renamer.py
```

Line length is set to 88 characters (Black default). Flake8 is configured to
match via `[tool.flake8]` in `pyproject.toml`.

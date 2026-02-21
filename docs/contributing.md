# Contributing to Optopsy

Thank you for your interest in contributing to Optopsy! This guide will help you get started.

## Development Setup

### 1. Clone the Repository

```bash
git clone https://github.com/michaelchu/optopsy.git
cd optopsy
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Development Dependencies

```bash
pip install -e ".[ui]"
pip install pytest ruff mypy
```

### 4. Verify Installation

```bash
pytest tests/ -v
```

## Development Workflow

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_strategies.py -v

# Run tests matching a pattern
pytest tests/ -k "butterfly" -v
```

### Code Formatting and Linting

Optopsy uses [Ruff](https://github.com/astral-sh/ruff) for formatting and linting:

```bash
# Check formatting
ruff format --check optopsy/ tests/ setup.py

# Auto-format code
ruff format optopsy/ tests/ setup.py

# Lint code
ruff check optopsy/ tests/ setup.py

# Lint and auto-fix
ruff check --fix optopsy/ tests/ setup.py

# Type check
mypy optopsy/
```

**Important:** All code must pass `ruff format`, `ruff check`, and `mypy` before submitting a PR.

## Adding a New Strategy

Follow these steps to add a new options strategy:

### 1. Define Strategy in `strategies.py`

Add a public function and helper if needed:

```python
def new_strategy(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate new strategy statistics.

    A clear description of what this strategy does, including:
    - Leg composition
    - Market outlook
    - Profit/loss characteristics

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with strategy performance statistics
    """
    return _helper(data, leg_def=[...], **kwargs)
```

### 2. Add Validation Rules (if needed)

If your strategy has strike constraints, add them to `rules.py`:

```python
def _rule_new_strategy_strikes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validate strike ordering for new strategy.

    Rule: [Describe your rule here]
    """
    # Implementation
    return df[mask]
```

### 3. Update Column Definitions (if needed)

If your strategy needs new column structures, add them to `definitions.py`:

```python
new_strategy_internal_cols: List[str] = [
    "underlying_symbol",
    "strike_leg1",
    # ... other columns
]
```

### 4. Export in `__init__.py`

Add your strategy to the exports:

```python
from .strategies import (
    # ... existing strategies
    new_strategy,
)

__all__ = [
    # ... existing strategies
    "new_strategy",
]
```

### 5. Add Tests

Create tests in `tests/test_strategies.py`:

```python
def test_new_strategy(sample_data):
    """Test new strategy returns expected output."""
    results = op.new_strategy(sample_data)

    assert isinstance(results, pd.DataFrame)
    assert len(results) > 0
    assert 'mean' in results.columns
    # Additional assertions
```

### 6. Update Documentation

Add documentation to the appropriate strategy category file in `docs/strategies/`.

## Pull Request Guidelines

### Before Submitting

- [ ] All tests pass (`pytest tests/ -v`)
- [ ] Code is formatted with Ruff (`ruff format optopsy/ tests/ setup.py`)
- [ ] Linting passes (`ruff check optopsy/ tests/ setup.py`)
- [ ] Type checking passes (`mypy optopsy/`)
- [ ] New features have tests
- [ ] New strategies have documentation
- [ ] Docstrings follow existing style (Google format)
- [ ] Type hints are included

### PR Description

Include in your PR description:
- What changes you made
- Why you made them
- How to test the changes
- Any breaking changes

### Example PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How to test these changes

## Checklist
- [ ] Tests pass
- [ ] Code formatted with Ruff
- [ ] Documentation updated
- [ ] Type hints included
```

## Code Style Guidelines

### Docstrings

Use Google-style docstrings:

```python
def function_name(param1: str, param2: int) -> bool:
    """
    Brief description of function.

    Longer description if needed, explaining behavior,
    edge cases, or important details.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ValueError: When param1 is invalid
    """
    pass
```

### Type Hints

Always include type hints:

```python
from typing import Any, Dict, List
import pandas as pd

def process_data(
    data: pd.DataFrame,
    params: Dict[str, Any]
) -> List[pd.DataFrame]:
    ...
```

### Function Naming

- Public functions: `snake_case` (e.g., `long_calls`)
- Private functions: `_snake_case` (e.g., `_process_strategy`)
- Constants: `UPPER_CASE` (rarely used)

## Testing Guidelines

### Test Structure

```python
def test_feature_name(sample_data):
    """Test that feature behaves correctly."""
    # Arrange
    expected_result = ...

    # Act
    actual_result = function_under_test(sample_data)

    # Assert
    assert actual_result == expected_result
```

### Fixtures

Use pytest fixtures for common test data:

```python
@pytest.fixture
def sample_data():
    """Generate sample options data for testing."""
    return pd.DataFrame({...})
```

### Coverage

Aim for high test coverage on public APIs. Not every internal function needs tests, but all public strategy functions should be tested.

## Documentation

### Building Docs Locally

```bash
# Install MkDocs
pip install mkdocs mkdocs-material mkdocstrings[python]

# Serve docs locally
mkdocs serve

# Visit http://127.0.0.1:8000
```

### Documentation Structure

- `docs/index.md` - Home page
- `docs/getting-started.md` - Installation and quick start
- `docs/strategies/` - Strategy-specific documentation
- `docs/parameters.md` - Parameter reference
- `docs/examples.md` - Usage examples
- `docs/api-reference.md` - Auto-generated API docs

## Reporting Issues

### Bug Reports

Include:
- Python version
- Optopsy version
- Minimal reproducible example
- Expected vs actual behavior
- Error messages/tracebacks

### Feature Requests

Describe:
- The problem you're trying to solve
- How you envision the solution
- Any alternatives you've considered
- Whether you're willing to contribute the feature

## Community

- **GitHub Issues**: Bug reports and feature requests
- **Discussions**: Questions and general discussion
- **Pull Requests**: Code contributions

## License

By contributing to Optopsy, you agree that your contributions will be licensed under the GPL-3.0 License.

## Questions?

If you have questions about contributing, feel free to:
- Open a GitHub Discussion
- Create an issue with the "question" label
- Check existing issues and documentation

Thank you for contributing to Optopsy!

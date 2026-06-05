# Givebutter Processor - Testing Guide

Comprehensive test suite for the Givebutter CSV processor with validation, duplicate detection, and operator review workflow.

> **Latest Update (2026-06-05):** Added column structure regression tests and pre-commit hook to prevent template rendering bugs. Covers processor output validation and table DOM alignment. All 271 tests passing (9 new). Tests automatically run before each commit.

## Test Structure

```
tests/
├── unit/                          # Unit tests for individual functions
│   ├── test_validation_email.py   # Email validation tests
│   ├── test_validation_phone.py   # Phone validation tests
│   ├── test_validation_amount.py  # Amount validation tests
│   ├── test_validation_name.py    # Name validation tests
│   ├── test_validation_address.py # Address validation tests
│   ├── test_validation_header.py  # Header mapping tests
│   ├── test_tier_assignment.py    # Tier assignment logic tests
│   └── test_field_validation_edge_cases.py # Edge cases for all fields (NEW)
│
├── integration/                   # Integration tests for processor pipeline
│   ├── test_processor_full.py     # Full processor pipeline tests
│   ├── test_decision_persistence.py # Decision saving/loading tests
│   ├── test_csv_formats.py        # CSV format handling tests
│   ├── test_edit_persistence.py   # Inline edit persistence tests
│   └── test_column_structure.py   # Column output validation tests (NEW 2026-06-05)
│
├── e2e/                           # End-to-end UI tests with Playwright
│   ├── test_e2e_upload_workflow.py # Upload workflow tests
│   ├── test_e2e_decision_workflow.py # Decision review workflow tests
│   ├── test_e2e_inline_editing.py # Inline editing feature tests
│   ├── test_e2e_visual_regression.py # Visual regression tests
│   ├── test_e2e_form_input.py     # Form interaction tests
│   ├── test_e2e_csv_format_variations.py # CSV format variation tests
│   ├── test_e2e_override_dialog_ui.py # Override confirmation dialog tests
│   └── test_e2e_table_structure.py # Table column alignment tests (NEW 2026-06-05)
│
├── conftest.py                    # Pytest fixtures and configuration
└── pytest.ini                     # Pytest configuration

```

## Installation

### 1. Install Test Dependencies

```bash
cd Givebutter
pip install -r requirements-test.txt
```

Contents of `requirements-test.txt`:
```
pytest==7.4.3
pytest-asyncio==0.21.1
playwright==1.40.0
requests==2.31.0
```

### 2. Install Playwright Browsers (for E2E tests)

```bash
playwright install chromium
```

## Pre-Commit Hook (Automatic Testing)

Tests automatically run before each commit via `.git/hooks/pre-commit`. This prevents regressions from being committed without being caught by tests.

**If a commit fails due to test failures:**
```bash
# Fix the failing tests
pytest tests/ -v  # Identify and fix issues

# Try commit again
git commit -m "..."
```

To bypass the hook (not recommended):
```bash
git commit --no-verify
```

## Running Tests

### Run All Tests
```bash
pytest tests/ -v
```

### Run Tests by Type

**Unit Tests Only:**
```bash
pytest tests/unit/ -v
```

**Integration Tests Only:**
```bash
pytest tests/integration/ -v
```

**E2E Tests Only:**
```bash
pytest tests/e2e/ -v
```

### Run Tests by Marker

```bash
# Only unit tests
pytest -m unit -v

# Only integration tests
pytest -m integration -v

# Only E2E tests
pytest -m e2e -v

# Only visual regression tests
pytest -m visual -v

# Only form/input tests
pytest -m form -v

# Skip slow tests
pytest -m "not slow" -v

# Only slow tests
pytest -m slow -v

# Visual and form tests combined
pytest -m "visual or form" -v
```

### Run Specific Test File

```bash
pytest tests/unit/test_validation_email.py -v
```

### Run Specific Test Function

```bash
pytest tests/unit/test_validation_email.py::TestEmailValidation::test_valid_email -v
```

### Run with Coverage

```bash
pip install pytest-cov
pytest tests/ --cov=scripts --cov-report=html
# View coverage report: open htmlcov/index.html
```

## Test Fixtures (conftest.py)

### Available Fixtures

- **temp_dir**: Temporary directory for test files
- **sample_csv**: Sample CSV with 4 test records (John, Jane, Bob, Alice)
- **rules_config**: Configuration with email typos and phone patterns
- **reference_config**: Reference lists for domains, TLDs, and thresholds

### Example Usage

```python
def test_something(temp_dir, sample_csv, rules_config, reference_config):
    # Use fixtures in your test
    output_file = temp_dir / "output.csv"
    process_csv(str(sample_csv), str(output_file))
```

## Unit Tests Overview

### test_validation_email.py
- Valid email detection
- Email typo detection (gmai.com → gmail.com, etc.)
- Multiple typo patterns
- Invalid email format (missing @)
- Empty email handling
- Missing email column
- Case-insensitive comparison

### test_validation_phone.py
- Valid 10-digit and 11-digit US phone numbers
- Standard and unusual formatting
- Invalid phone patterns (test numbers, sequential)
- Phone too short/long validation
- Missing phone column warning
- Area code validation
- Whitespace handling

### test_validation_amount.py
- Valid amounts with various formats ($, comma-separated)
- Zero/negative amount rejection
- Amount range validation
- High-dollar donation flagging ($1000+)
- Custom threshold support
- Missing amount detection
- Invalid format handling

### test_validation_name.py
- Name length validation (min/max)
- Empty name detection
- Missing name column
- Special characters (O'Brien, José García)
- Unicode/international characters (中文)
- Custom length requirements

### test_validation_address.py
- Complete address validation
- Incomplete address detection
- Missing column handling
- Special characters in addresses
- International addresses
- UTF-8 character preservation

### test_validation_header.py
- Core header exact matching
- Fuzzy header matching (variations)
- Precedence: core headers before fuzzy
- Whitespace handling in headers
- Missing optional columns
- Custom column order support
- Case-sensitive matching

### test_tier_assignment.py
- PASS tier when all validations pass
- FAIL tier takes precedence
- WARNING tier without FAIL
- Multiple failures/warnings
- Empty validation results
- Duplicate detection integration

## Integration Tests Overview

### test_processor_full.py
- Full processor pipeline end-to-end
- Validation tier assignment
- Email typo detection in CSV
- Missing data handling
- Original columns preservation
- Column ordering
- High-dollar donation detection
- Invalid phone detection
- UTF-8 character preservation
- Empty row handling
- Summary statistics output
- Large CSV processing (100+ records)

### test_decision_persistence.py
- Single decision saving
- Multiple decision saving
- Partial save with existing decisions
- Decision overwrites
- Notes with special characters
- Undecided count calculation
- UTF-8 in operator notes
- Column initialization

### test_csv_formats.py
- Extra trailing columns
- Inconsistent row column counts
- Quoted fields with commas
- Line breaks in quoted fields
- Windows (CRLF) line endings
- Whitespace in headers
- Custom column order
- Duplicate column names
- Special characters in data
- Empty fields
- UTF-8 BOM marker
- Currency formatting ($, commas)
- Single-row CSV
- Numeric string preservation

### test_column_structure.py (NEW 2026-06-05)
Regression tests to prevent template rendering bugs:
- All required data columns present in processor output
- Validation columns (Validation_Tier, Issues, Suggested_Modifications) always added
- Validation columns positioned at end of output
- Fuzzy column name matching works correctly
- Original CSV columns preserved and not lost during processing

**Why:** Catches bugs where columns are accidentally removed, reordered, or rendered in wrong positions.

## E2E Tests Overview

### test_e2e_upload_workflow.py
- Page loads successfully
- File upload through UI
- Validation results display
- Invalid file type rejection
- Processing queue listing
- File appears in queue after upload
- Special characters in filenames/data
- Large CSV upload (100+ records)

Requires:
- Flask app running at `http://127.0.0.1:8000`
- Playwright with Chromium browser

### test_e2e_decision_workflow.py
- View records for review
- Select decision from dropdown
- Add operator notes
- Save decisions (partial save)
- Save all decisions (complete review)
- Decision persistence on reopen
- Cancel review workflow
- Page scrolls to top on load

Requires:
- Flask app running at `http://127.0.0.1:8000`
- Playwright with Chromium browser

### test_e2e_visual_regression.py
Visual regression testing with Playwright screenshots:
- Page screenshots at different viewport sizes
- Mobile (375px), tablet (768px), desktop (1280px, 1920px)
- Upload page appearance
- Processing queue display
- Review table layout
- Decision dropdown rendering
- Notes textarea display
- Error message appearance
- Success message display
- Screenshot baseline comparison
- Automatic diff image generation

Features:
- Captures full-page screenshots
- Responsive design testing
- Layout stability detection
- Visual regression detection via PIL image comparison
- Configurable comparison threshold (default 1% difference allowed)

Usage:
```bash
# Capture screenshots (saves as baseline on first run)
pytest tests/e2e/test_e2e_visual_regression.py -v

# Compare against baseline
pytest tests/e2e/test_e2e_visual_regression.py::test_screenshot_regression_upload_page -v

# Generate diff images on failure
# Diff images saved to screenshots/diff/
```

Requires:
- Playwright with Chromium
- Optional: Pillow (PIL) for screenshot comparison

### test_e2e_form_input.py
Form and input interaction testing:

**File Upload Tests**:
- File input accepts CSV
- File selection feedback
- Upload button state
- Loading feedback

**Decision Dropdown Tests**:
- All options present (approved, followup, rejected)
- Visual state on selection
- Keyboard navigation (arrow keys)
- Value preservation

**Notes Textarea Tests**:
- Text input acceptance
- Unicode/special character support
- Placeholder text hints
- Keyboard navigation (Tab)

**Validation Feedback Tests**:
- Validation summary clarity
- Tier color coding

**Save/Submission Tests**:
- Clear button labels
- Success message feedback
- Cancel confirmation
- Form state management

Usage:
```bash
# Run all form tests
pytest tests/e2e/test_e2e_form_input.py -v

# Run specific category
pytest tests/e2e/test_e2e_form_input.py -k "dropdown" -v
pytest tests/e2e/test_e2e_form_input.py -k "textarea" -v
pytest tests/e2e/test_e2e_form_input.py -k "save" -v
```

Requires:
- Flask app running at `http://127.0.0.1:8000`
- Playwright with Chromium browser

### test_e2e_table_structure.py (NEW 2026-06-05)
DOM structure and column alignment tests:
- Review table has all 15 expected header columns in correct order
- Each data row has exactly as many cells as headers
- Date column is always present and populated
- No extra columns are rendered (prevents misalignment)

**Why:** Catches column alignment bugs that would otherwise only be discovered by manually testing the UI. Regression prevention for template rendering issues.

Usage:
```bash
# Run all table structure tests
pytest tests/e2e/test_e2e_table_structure.py -v
```

Requires:
- Flask app running at `http://127.0.0.1:8000`
- Playwright with Chromium browser

## Running E2E Tests

### Option 1: Using Provided Fixture
The test files include `start_flask_app` fixture that starts the Flask app automatically.

```bash
pytest tests/e2e/ -v -s
```

### Option 2: Manual Flask Start
Start Flask separately:

```bash
# Terminal 1
cd scripts/uploader
python3 app.py

# Terminal 2
pytest tests/e2e/ -v
```

## Test Configuration (pytest.ini)

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short

markers =
    unit: Unit tests for individual functions
    integration: Integration tests for processor
    e2e: End-to-end tests with UI
    slow: Tests that take longer to run
```

## Sample Test Data

### sample_csv (from conftest.py)
```csv
Donation ID,Date,Donor Name,Email,Amount
GB001,2026-05-25,John Smith,john@gmail.com,100.00
GB002,2026-05-25,Jane Doe,jane@gmai.com,50.00
GB003,2026-05-25,Bob Wilson,bob@yahoo.com,75.00
GB004,2026-05-25,Alice Brown,alice@yaho.com,200.00
```

### rules_config
Email typos:
- gmai.com → gmail.com
- gmal.com → gmail.com
- yaho.com → yahoo.com
- yahooo.com → yahoo.com
- hotmial.com → hotmail.com
- hotmal.com → hotmail.com
- outlok.com → outlook.com

Phone patterns:
- `^1234567890$` - Sequential test number
- `^(\d)\1{9}$` - All same digit
- `^555[0-1]\d{6}$` - Reserved test number

### reference_config
- Email domains: gmail.com, yahoo.com, hotmail.com, outlook.com
- Email TLDs: com, org, net, edu
- Amount range: $1-$100,000
- High-dollar threshold: $1,000
- Name length: 2-100 characters

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - run: pip install -r requirements-test.txt
      - run: playwright install chromium
      - run: pytest tests/ -v
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'pandas'"
Install required dependencies:
```bash
pip install -r requirements-test.txt
```

### Playwright tests fail to start browser
Install Playwright browsers:
```bash
playwright install chromium
```

### "Address already in use" for E2E tests
Flask app is already running on port 8000. Either:
1. Kill the existing process: `lsof -ti:8000 | xargs kill`
2. Stop the manual Flask server if running
3. Wait for fixture to clean up from previous test run

### Tests timeout
- Increase timeout in pytest: `pytest --timeout=300 tests/`
- For E2E tests, increase `timeout` in page operations

## Performance Notes

- Unit tests: < 1 second each
- Integration tests: < 2 seconds each
- E2E tests: 5-30 seconds each (includes UI interaction)
- Large CSV test (100 records): ~5 seconds
- All tests together: ~3-5 minutes

## Writing New Tests

### Template: Unit Test

```python
import pytest
from processor import validate_something

class TestValidateSomething:
    """Test validate_something function."""

    @pytest.mark.unit
    def test_valid_case(self):
        """Test valid input."""
        result = validate_something(input_data)
        assert result == expected_value

    @pytest.mark.unit
    def test_invalid_case(self):
        """Test invalid input."""
        result = validate_something(bad_input)
        assert result == expected_error
```

### Template: Integration Test

```python
import pytest
import pandas as pd
from processor import process_csv

class TestProcessorFeature:
    """Test processor feature."""

    @pytest.mark.integration
    def test_feature(self, temp_dir, rules_config, reference_config):
        """Test specific feature."""
        # Setup
        csv_file = temp_dir / "test.csv"
        csv_file.write_text(csv_content)

        # Execute
        output_file = temp_dir / "output.csv"
        process_csv(str(csv_file), str(output_file))

        # Assert
        df = pd.read_csv(output_file, dtype=str, encoding='utf-8')
        assert len(df) > 0
```

### Template: E2E Test

```python
import pytest

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_ui_feature(flask_app_running, temp_dir):
    """Test UI feature."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            await page.goto("http://127.0.0.1:8000/")
            # Your test steps here
            assert True
        finally:
            await browser.close()
```

## Best Practices

1. **Isolation**: Each test should be independent and not rely on test order
2. **Fixtures**: Use conftest.py fixtures for setup/teardown
3. **Markers**: Tag tests with @pytest.mark.unit/integration/e2e for selective running
4. **Names**: Use descriptive test function names (test_what_when_then)
5. **Cleanup**: Tests clean up automatically with temp_dir fixture
6. **UTF-8**: Always use encoding='utf-8' in file operations
7. **Error Messages**: Include assertion messages for clarity
8. **Timeouts**: E2E tests should have explicit waits, not fixed sleeps

## Maintenance

### Updating Test Data
Modify `conftest.py` fixtures when test data structures change.

### Adding New Validation Rules
Add corresponding test cases in appropriate `test_validation_*.py` file.

### Changing Flask Routes
Update E2E tests in `test_e2e_*.py` files to match new route paths.

### Performance Regressions
Monitor test execution times. Use `@pytest.mark.slow` for long-running tests.

## Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Playwright Documentation](https://playwright.dev/python/)
- [Pandas Testing Guide](https://pandas.pydata.org/docs/development/testing.html)

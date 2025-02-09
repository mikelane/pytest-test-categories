# Pytest Test Categories Plugin

## Overview

**Pytest Test Categories** is a plugin designed to help developers enforce test timing constraints and size distributions in their test suites. This plugin provides an effective way to categorize tests by their execution time and ensures that the test distribution meets predefined targets for different test sizes.

The test size categories and their time limits are based on recommendations from Google's "Software Engineering at Google" book. The plugin offers size markers such as `small`, `medium`, `large`, and `xlarge`, each with specific time constraints.

## Features

- **Categorization of tests by size:** Mark tests with predefined size markers to categorize them based on execution time.
- **Time limit enforcement:** Automatically fail tests that exceed their allocated time limit.
- **Test distribution validation:** Ensure that your test suite's size distribution adheres to best practices.
- **Plugin configuration and hooks:** Integrates with pytest's hook system to provide seamless functionality.

## Test Size Categories and Time Limits

| Size    | Time Limit  |
|---------|-------------|
| Small   | 1 second    |
| Medium  | 5 minutes   |
| Large   | 15 minutes  |
| XLarge  | 15 minutes  |

## Installation

This project uses [Poetry](https://python-poetry.org/) for dependency management. You can install the project by running:

```bash
poetry install
```

## Usage

Mark your tests with size markers to categorize them. For example:

```python
import pytest

@pytest.mark.small
def test_fast_function():
    assert some_function() == expected_result

@pytest.mark.medium
def test_moderate_function():
    assert some_other_function() == another_result
```

Run pytest as usual:

```bash
poetry run pytest
```

## Development

This project follows best practices for testing, linting, and code quality.

### Install Development Dependencies

```bash
poetry install --no-root --all-groups
```

`--no-root` is required to avoid installing the package itself, which can result in plugin double-registration when running pytest.

### Setup Pre-commit Hooks

To ensure code quality, set up pre-commit hooks:

```bash
poetry run pre-commit install
```

### Running Tests and Linting

Use pre-commit to automatically run tests, check coverage, and format code. Pre-commit hooks ensure that these steps are performed consistently and that your code adheres to the project's style guidelines.

```bash
poetry run pre-commit run --all-files
```

## How It Works

The plugin hooks into several pytest phases to:

- Count tests by size during collection
- Validate the test distribution at the end of collection
- Enforce time limits during test execution
- Modify the test report to display size labels next to test names

### Key Hooks

- `pytest_configure`: Registers the plugin and size markers
- `pytest_collection_modifyitems`: Tracks the number of tests in each size category
- `pytest_collection_finish`: Validates the distribution of test sizes
- `pytest_runtest_protocol`: Tracks the execution time of each test

## Test Distribution Targets

| Size         | Target Percentage | Tolerance |
|--------------|-------------------|-----------|
| Small        | 80%               | 5%        |
| Medium       | 15%               | 5%        |
| Large/XLarge | 5%                | 3%        |

## Contributing

We welcome contributions from the community! Here are some ways you can contribute:

- **Report bugs:** If you find a bug, please open an issue.
- **Submit patches:** Feel free to fork the repository and submit a pull request.
- **Improve documentation:** Help us improve the documentation by making it clearer and more comprehensive.

### Recommended Fork Workflow

To contribute to this project, follow these steps:

1. **Fork the repository using GitHub CLI:**
   - Use the following command to fork the repository, clone it to your local machine, and set the remote:

   ```bash
   gh repo fork mikelane/pytest-test-categories --clone --remote
   cd pytest-test-categories
   ```

2. **Create a new branch:**
   - It is recommended to create a new branch for each feature or bug fix:

   ```bash
   git checkout -b your-feature-branch
   ```

3. **Make your changes:**
   - Implement your feature or bug fix in your local repository.

4. **Run pre-commit hooks:**
   - Use pre-commit to ensure your changes pass all checks:

   ```bash
   poetry run pre-commit run --all-files
   ```

5. **Commit your changes:**
   - Use descriptive commit messages:

   ```bash
   git add .
   git commit -m "Add feature X to improve Y"
   ```

6. **Push your branch to your fork:**

   ```bash
   git push origin your-feature-branch
   ```

7. **Open a Pull Request (PR):**
   - Use the GitHub CLI to open a pull request:

   ```bash
   gh pr create --title "Add feature X" --body "Description of the changes."
   ```

8. **Address feedback:**
   - Be responsive to feedback from maintainers and make any necessary changes.

## License

This project is available under a dual-license model:

- **Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0):** You are free to use, modify, and distribute the project for non-commercial purposes, provided that you give appropriate credit.

- **Commercial License:** If you wish to use this project in a commercial setting, please contact me at [mikelane@gmail.com](mailto:mikelane@gmail.com) to obtain a commercial license.

See the [LICENSE](LICENSE) file for details.

---

Happy testing!

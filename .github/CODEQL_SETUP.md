# CodeQL Advanced Setup Configuration

This repository uses **CodeQL Advanced Setup** for code security scanning, which provides more control and flexibility than GitHub's default setup.

## Why Advanced Setup?

Our advanced CodeQL configuration provides:

- **Extended security queries**: Uses the `security-and-quality` query suite for comprehensive vulnerability detection
- **Custom language configurations**: Fine-tuned analysis for Python 3.14 with explicit dependency installation
- **CI/CD integration**: Runs as part of our security workflow with uv-based dependency management
- **Consistent scanning**: Controlled execution across all branches and pull requests
- **Custom scheduling**: Daily security scans at 2 AM UTC via cron schedule

## Required Repository Settings

**IMPORTANT**: GitHub does not allow both default setup and advanced setup to be enabled simultaneously. You must disable the default setup before the advanced configuration will work.

### Step-by-Step Instructions

1. **Navigate to repository settings**
   - Go to your repository on GitHub
   - Click **Settings** (requires admin access)

2. **Access Code Security settings**
   - In the left sidebar, click **Code security and analysis**

3. **Disable CodeQL default setup**
   - Find the **Code scanning** section
   - Look for **CodeQL analysis** - it will show "Default" if default setup is enabled
   - Click the **⋯** (three dots menu) next to "Default"
   - Select **Disable CodeQL default setup**
   - Confirm the action in the dialog

   **Note**: If you see a "Set up" button instead of "Default", the default setup is not currently enabled, and you can skip this step.

4. **Verify advanced setup is active**
   - After disabling default setup, our workflow in `.github/workflows/security.yml` will automatically run
   - Check the **Actions** tab to see the security workflow executing
   - View results in the **Security** tab under **Code scanning alerts**

## Troubleshooting

### Error: "CodeQL analyses from advanced configurations cannot be processed when the default setup is enabled"

**Cause**: GitHub's default CodeQL setup is still enabled in repository settings.

**Solution**: Follow the steps above to disable default setup.

### Workflow runs but no results appear

**Cause**: The workflow may need permissions to write security events.

**Solution**: Check that the workflow has the following permissions in `security.yml`:
```yaml
permissions:
  contents: read
  security-events: write
```

### Analysis fails during build

**Cause**: CodeQL needs to understand how to build Python dependencies.

**Solution**: Our workflow includes explicit Python 3.14 setup, `uv` installation, and dependency installation (`uv sync --all-groups`). If you see build errors, check that `pyproject.toml` is correctly configured.

## Workflow Configuration

The advanced setup is configured in `.github/workflows/security.yml` in the `codeql-analysis` job:

```yaml
codeql-analysis:
  name: CodeQL Analysis
  runs-on: ubuntu-latest
  timeout-minutes: 15
  permissions:
    security-events: write
    actions: read
    contents: read

  steps:
    - name: Checkout code
      uses: actions/checkout@v5

    - name: Initialize CodeQL
      uses: github/codeql-action/init@v3
      with:
        languages: python
        queries: security-and-quality

    - name: Set up Python
      uses: actions/setup-python@v6
      with:
        python-version: '3.14'

    - name: Install uv
      uses: astral-sh/setup-uv@v7

    - name: Install dependencies
      run: uv sync --all-groups

    - name: Perform CodeQL Analysis
      uses: github/codeql-action/analyze@v3
      with:
        category: "/language:python"
```

## Switching Between Default and Advanced

### To switch from Advanced → Default:
1. Remove or comment out the `codeql-analysis` job in `.github/workflows/security.yml`
2. Go to Settings → Code security and analysis
3. Enable CodeQL default setup

### To switch from Default → Advanced:
1. Follow the "Required Repository Settings" steps above to disable default setup
2. Ensure the `codeql-analysis` job exists in `.github/workflows/security.yml`
3. Push changes and verify the workflow runs successfully

## References

- [CodeQL Documentation](https://codeql.github.com/docs/)
- [GitHub Code Scanning](https://docs.github.com/en/code-security/code-scanning)
- [Default vs Advanced Setup](https://docs.github.com/en/code-security/code-scanning/automatically-scanning-your-code-for-vulnerabilities-and-errors/configuring-code-scanning-for-a-repository)
- [CodeQL Query Suites](https://docs.github.com/en/code-security/code-scanning/creating-an-advanced-setup-for-code-scanning/codeql-query-suites)

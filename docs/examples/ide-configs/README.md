# IDE Configuration Examples

This directory contains example IDE configuration files for use with pytest-test-categories.

## VS Code

Copy these files to your project's `.vscode/` directory:

| File | Purpose |
|------|---------|
| `vscode-settings.json` | Copy to `.vscode/settings.json` - Basic pytest and coverage configuration |
| `vscode-tasks.json` | Copy to `.vscode/tasks.json` - Task definitions for running tests by size |
| `vscode-launch.json` | Copy to `.vscode/launch.json` - Debug configurations for tests by size |

### Quick Setup

```bash
# Create .vscode directory if it doesn't exist
mkdir -p .vscode

# Copy configurations (rename as appropriate)
cp vscode-settings.json .vscode/settings.json
cp vscode-tasks.json .vscode/tasks.json
cp vscode-launch.json .vscode/launch.json
```

### Customization

After copying, you may want to customize:

- **settings.json**: Update `python.defaultInterpreterPath` if your virtual environment is in a different location
- **tasks.json**: Add project-specific test commands or modify existing ones
- **launch.json**: Adjust `justMyCode` setting based on your debugging needs

## PyCharm

PyCharm stores run configurations in `.idea/runConfigurations/`. These are typically user-specific and may contain absolute paths.

### Recommended Approach for PyCharm

Instead of copying configuration files, create run configurations manually:

1. Open **Run > Edit Configurations**
2. Click **+** and select **pytest**
3. Configure:
   - **Name**: "Small Tests" (or appropriate name)
   - **Target**: Select your test directory
   - **Additional Arguments**: `-m small` (or other marker expression)
4. Repeat for each test size category

### Sharing PyCharm Configurations

If you want to share configurations with your team, you can include `.idea/runConfigurations/` in version control. Create files like:

- `.idea/runConfigurations/Small_Tests.xml`
- `.idea/runConfigurations/Medium_Tests.xml`
- `.idea/runConfigurations/Large_Tests.xml`

See the [PyCharm documentation](https://www.jetbrains.com/help/pycharm/sharing-run-debug-configurations-as-files.html) for more details.

## Usage

For complete documentation on IDE integration, see the [IDE Integration Guide](../../ide-integration.md).

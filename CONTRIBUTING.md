# Contributing

Thank you for helping improve DSNS PDF Pro.

## Development setup

1. Fork and clone the repository.
2. Create a virtual environment.
3. Install development dependencies:

   ```powershell
   py -m pip install -r requirements-dev.txt
   ```

4. Run the application:

   ```powershell
   .\start.ps1
   ```

## Before submitting a pull request

Run the complete validation suite:

```powershell
node --check .\static\workflows.js
py -m pytest -q
```

Keep changes focused, add tests for behavior changes, and update documentation when user-facing behavior changes. Do not include uploaded documents, generated PDFs, credentials, or personal data in commits or test fixtures.

## Pull requests

- Explain the problem and the chosen solution.
- Describe manual testing performed.
- Link related issues.
- Confirm that tests pass locally.

By contributing, you agree that your contribution is licensed under the MIT License.

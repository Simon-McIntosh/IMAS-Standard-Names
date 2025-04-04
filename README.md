[![pre-commit][pre-commit-badge]][pre-commit-link]
[![Ruff][ruff-badge]][ruff-link]
[![Python versions][python-badge]][python-link]
[![CI/CD status][build-deploy-badge]][build-deploy-link]
[![Coverage status][codecov-badge]][codecov-link]
[![Documentation][docs-badge]][docs-link]

# IMAS Standard Names

This repository documents a collection of Standard Names used in the Fusion Conventions. To submit proposals for new Standard Names or changes to existing Standard Names, please use one of the supplied issue templates. The issue templates use the following "zero-code" submission process:

1. **Create an Issue**: Use the provided issue templates to create a new issue.
   - For new Standard Names, use the "New Standard Name" template.
   - For changes to existing Standard Names, use the "Change Existing Standard Name" template.
2. **Fill in the Template**: Provide all required information in the issue template.
   - For new Standard Names, include details such as the proposed name, description, and any relevant references.
   - For changes to existing Standard Names, specify the name of the existing Standard Name and the proposed changes.
3. **Submit the Issue**: Once you have filled in the template, submit the issue.
4. **Review Process**: We outline the review process as follows:
   - Following submission, a GitHub action will automatically check the issue for compliance with the Fusion Conventions and flag any errors or missing information.
   - After successful automatic processing, a member of the IMAS Standard Names team will review your issue.
   - The team may request information or clarification if needed.
5. **Approval**: Once your issue is sufficiently developed, collaborators with privileges will tag it with the 'approve' label.
6. **Submission**: After approval, a GitHub action will automatically commit the Standard Name proposal to the `submit` branch. The action will raise a *draft* Pull Request pointing from the `submit` branch to the `develop` branch, if one is not already present.
7. **Final Review**: Once we collect a batch of Standard Name proposals, the Pull Request will undergo final review and approval.
8. **Release**: We will tag releases that merge approved changes from the `develop` branch back to the `main` branch accordingly.
9. **Feedback**: We encourage feedback on the Standard Names to ensure they meet community needs. Please submit your feedback through the provided issue templates to support discussion and improvements.

## Branching Strategy

This project uses a Git branching strategy to manage development and releases. The principal branches are:

- The `submit` branch collects and reviews proposed changes to the Standard Names.
- We use the `develop` branch for ongoing development and testing of new Standard Names.
- We create tagged releases of the Standard Names project and associated documentation from the `main` branch.

## Documentation

The project documentation is available at our [GitHub Pages site](https://Simon-McIntosh.github.io/IMAS-Standard-Names/).

GitHub Actions automatically build and deploy the documentation whenever you push changes to the main branch. We version the documentation using [Mike](https://github.com/jimporter/mike), allowing versions to be accessible simultaneously.

### Local Documentation Development

To build the documentation locally, run:

```bash
# create virtual environment
python -m venv
. venv/bin/activate

# Install documentation dependencies
pip install .[docs]

# Build the documentation
mkdocs build

# To preview the documentation locally
mkdocs serve
```

### Working with Versioned Documentation

This project uses Mike to manage versioned documentation. To work with versioned documentation locally:

```bash
# Install documentation dependencies (includes Mike)
pip install .[docs]

# Initialize a git repo if not already done
git init

# Build and serve versions using Mike
mike deploy 0.1 latest --update-aliases
mike deploy 0.2 --update-aliases
mike serve  # Serves the versioned documentation locally

# List all versions of the documentation
mike list

# Set the default version
mike set-default latest
```

When the CI/CD pipeline runs, it automatically deploys documentation for:

- `main` branch as "latest"
- `develop` branch as "develop"
- `submit` branch as "submit"

Each branch will be available as a separate version in the version selector dropdown on the documentation site.

[python-badge]: https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue
[python-link]: https://github.com/Simon-McIntosh/IMAS-Standard-Names.git
[ruff-badge]: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json
[ruff-link]: https://docs.astral.sh/ruff/
[pre-commit-badge]: https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white
[pre-commit-link]: https://github.com/pre-commit/pre-commit
[build-deploy-badge]: https://img.shields.io/github/actions/workflow/status/Simon-McIntosh/IMAS-Standard-Names/python-package.yml?branch=main&color=brightgreen&label=CI%2FCD
[build-deploy-link]: https://codecov.io/gh/Simon-McIntosh/IMAS-Standard-Names/tests/main
[codecov-badge]: https://codecov.io/gh/Simon-McIntosh/IMAS-Standard-Names/graph/badge.svg
[codecov-link]: https://codecov.io/gh/Simon-McIntosh/IMAS-Standard-Names
[docs-badge]: https://img.shields.io/badge/docs-online-brightgreen
[docs-link]: https://Simon-McIntosh.github.io/IMAS-Standard-Names/

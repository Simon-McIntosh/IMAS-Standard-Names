# Contributing to IMAS Standard Names

Thank you for your interest in contributing to the IMAS Standard Names project! This document provides guidelines and instructions to help you contribute effectively.

## Project Overview

IMAS Standard Names is a project that maintains standardized naming conventions for data in the fusion energy research community. The repository contains definitions, schemas, and tools for working with these standard names.

## How to Contribute

### Reporting Issues

If you find a problem or have a suggestion:

1. Check if the issue already exists in the [Issues](https://github.com/iterorganization/imas-standard-names/issues) section
2. If not, create a new issue with a clear title and detailed description
3. Include relevant examples or error messages

### Submitting Changes

1. Fork the repository
2. Create a new branch with a descriptive name
3. Make your changes
4. Ensure tests pass with 100% coverage for modified code and update the documentation accordingly
5. Submit a pull request with a clear description of the changes

### Development Setup

1. Fork the repository:

   - Navigate to the [repository page](https://github.com/iterorganization/imas-standard-names).
   - Click the "Fork" button in the top-right corner of the page.

2. Clone your forked repository:

   ```bash
   git clone https://github.com/<your-username>/imas-standard-names.git
   cd imas-standard-names
   ```

3. Set up your development environment:

   ```bash
   # Install dependencies
   pip install -e ".[test]"
   ```

   ```bash
   # Update static links to your forked repo
   update_links origin
   ```

4. Run tests:

   ```bash
   pytest --cov
   ```

5. Create PR

   - make edits
   - confirm tests are passing with 100% coverage for updates

   ```bash
   # Update static links to match the upstream remote
   update_links upstream
   ```

## Coding Standards

- Follow PEP 8 style guide for Python code
- Include docstrings for all functions, classes, and modules
- Write tests for new functionality
- Keep commits focused and related to a single issue when possible

## Review Process

1. All pull requests require review by at least one maintainer
2. Automated tests must pass
3. Update the documentation alongside code changes
4. Reviewers may request changes before merging

## Adding or Modifying Standard Names

1. Propose standard name using the IMAS Standard Name issue template
2. Ensure the proposed name follows the established naming conventions
3. Provide a units and clear documentation

## License

By contributing to this project, you agree to license your contributions under the project's license.

## Questions?

If you have questions about contributing, please open an issue or contact the maintainers.

Thank you for contributing to the IMAS Standard Names project!

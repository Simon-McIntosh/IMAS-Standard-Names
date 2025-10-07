# Contributing to IMAS Standard Names

!!! warning "Documentation Out of Date"
This contributing guide is currently out of date and needs to be updated to reflect the latest project structure and workflows. Please consult the project maintainers or open an issue if you have questions about contributing.

Thank you for your interest in contributing to the IMAS Standard Names project! This document provides guidelines and instructions to help you contribute effectively.

## Project Overview

IMAS Standard Names is a project that maintains standardized naming conventions for data in the fusion energy research community. The repository contains definitions, schemas, and tools for working with these standard names.

## How to Contribute

### Creating Standard Names

You can contribute to the IMAS Standard Names project by proposing new standard names. This repository provides a guided process for creating well-formatted standard names with proper documentation.

#### Using the Standard Name Prompt

The repository includes a special prompt file that helps you create standardized GitHub issues for new standard names:

1. Open VS Code with GitHub Copilot Chat enabled in Agent mode
2. Attach this prompt to your GitHub Copilot query using one of these methods:

   - Press Ctrl+Alt+/ and select the standard-name prompt file
   - Open the Command Palette (Ctrl+Shift+P or Cmd+Shift+P), type "GitHub Copilot: Apply Prompt", then select the prompt file
   - Type "@prompt" followed by the path: `@prompt .github/prompts/standard-name.prompt.md`

3. Instruct Copilot to generate a Standard Name using natural language
4. Review the generated content and iterate with Copilot if required
5. Ask Copilot to submit the issue

#### Using the MCP Server

This repository includes configuration for the Model Context Protocol (MCP) server, which provides schema information and documentation for IMAS data structures.

> **Note:** Using the IMAS MCP server requires a local Docker installation on your system.

##### VS Code Integration

The repository includes a `.vscode/mcp.json` configuration file that sets up the necessary MCP servers:

1. Install Docker on your system if not already installed
2. Open the project in VS Code with the GitHub Copilot extension enabled
3. When prompted, enter your GitHub Personal Access Token (Note: this PAT token needs read access to metadata and read/write access to actions, issues, and pull requests)
4. The MCP servers (IMAS and GitHub) will be accessible to Copilot for providing schema information and documentation

##### Manual Setup (Alternative)

If you prefer to run the MCP server manually:

1. Pull the IMAS MCP server Docker image:

   ```bash
   docker pull ghcr.io/imas-icc/imas-mcp-server:latest
   ```

2. Run the MCP server locally:

   ```bash
   docker run -p 5000:5000 ghcr.io/imas-icc/imas-mcp-server:latest
   ```

3. The server will be accessible at `http://localhost:5000`

#### Usage Examples

Here are some examples of using the standard name prompt with the MCP server:

**Example 1: Create a standard name for plasma current**

1. Attach the standard-name prompt using one of these methods:
   - Press Ctrl+Alt+/ and select the standard-name prompt file
   - Open the Command Palette (Ctrl+Shift+P or Cmd+Shift+P), type "GitHub Copilot: Apply Prompt", then select the prompt file
   - Type `@prompt .github/prompts/standard-name.prompt.md` in the chat
2. Ask GitHub Copilot one of the following:
   - "Create a standard name for plasma toroidal current"
   - Directly specify the variable name: "plasma toroidal current"
3. The prompt will guide you through creating a properly formatted issue with:
   - Appropriate naming convention
   - Mathematical definition
   - Usage examples
   - IMAS Data Dictionary references

**Example 2: Create a standard name for electron temperature**

1. Attach the standard-name prompt using one of these methods:
   - Press Ctrl+Alt+/ and select the standard-name prompt file
   - Open the Command Palette (Ctrl+Shift+P or Cmd+Shift+P), type "GitHub Copilot: Apply Prompt", then select the prompt file
   - Type `@prompt .github/prompts/standard-name.prompt.md` in the chat
2. Ask GitHub Copilot one of the following:
   - "Create a standard name for electron temperature profile"
   - Directly specify the variable name: "electron temperature profile"
3. Review and submit the generated issue

**Example 3: Using the MCP server to explore the IMAS Data Dictionary**

When creating a standard name, you can directly interact with the IMAS MCP server API to explore the IMAS Data Dictionary:

##### Using GitHub Copilot Chat

With the MCP server configured in your workspace (via the `.vscode/mcp.json` file), you can directly interact with the IMAS data structures through Copilot Chat:

1. Get an overview of an IDS:

   ```
   What is the core_profiles IDS in IMAS?
   ```

2. Find specific properties in an IDS:

   ```
   Where is electron temperature stored in the IMAS data model?
   ```

3. Understand relationships between structures:

   ```
   What's the relationship between equilibrium and core_profiles in IMAS?
   ```

4. Get help with standard naming conventions:
   ```
   How should I name a variable for electron temperature at the magnetic axis?
   ```

These direct interactions with the MCP server through Copilot can help you understand IMAS data structures when creating standard names.

##### Using the Web Browser

You can also explore the API using your web browser:

1. Open `http://localhost:5000/v1/list-schemas` to see all available schemas
2. Navigate to `http://localhost:5000/v1/documentation?name=core_profiles` to view documentation
3. Visit `http://localhost:5000/v1/schema?name=equilibrium` to examine the equilibrium schema

##### Using the MCP Server REST API

After starting the MCP server, you can access the API at `http://localhost:5000`:

1. List all available schemas:

   ```bash
   curl http://localhost:5000/v1/list-schemas
   ```

2. Get documentation for a specific schema (e.g., core_profiles):

   ```bash
   curl http://localhost:5000/v1/documentation?name=core_profiles
   ```

3. Get the full schema definition for a specific data structure:

   ```bash
   curl http://localhost:5000/v1/schema?name=core_profiles
   ```

### Reporting Issues

If you find a problem or have a suggestion:

1. Check if the issue already exists in the [Issues](https://github.com/iterorganization/imas-standard-names/issues) section.
2. If not, create a new issue with a clear title and detailed description.
3. Include relevant examples or error messages.

### Submitting Changes

1. Fork the repository.
2. Create a new branch with a descriptive name.
3. Make your changes.
4. Ensure tests pass with 100% coverage for modified code and update the documentation accordingly.
5. Submit a pull request with a clear description of the changes.

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

5. Create a PR:

   - Make edits.
   - Confirm tests are passing with 100% coverage for updates.

   ```bash
   # Update static links to match the upstream remote
   update_links upstream
   ```

## Coding Standards

- Follow PEP 8 style guide for Python code.
- Include docstrings for all functions, classes, and modules.
- Write tests for new functionality.
- Keep commits focused and related to a single issue when possible.

## Review Process

1. All pull requests require review by at least one maintainer.
2. Automated tests must pass.
3. Update the documentation alongside code changes.
4. Reviewers may request changes before merging.

## Adding or Modifying Standard Names

1. Propose a standard name using the IMAS Standard Name issue template.
2. Ensure the proposed name follows the established naming conventions.
3. Provide units and clear documentation.

## License

By contributing to this project, you agree to license your contributions under the project's license.

## Questions?

If you have questions about contributing, please open an issue or contact the maintainers.

Thank you for contributing to the IMAS Standard Names project!

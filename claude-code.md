## What Are Agents and How Are They Used in Claude Code?

**Agents** in Claude Code are specialized AI assistants, each with a dedicated role, context, and abilities. They help automate and organize complex development workflows by handling specific tasks such as designing, coding, testing, or reviewing software.

### How Agents Work

- **Definition**: Each agent is defined in a Markdown file within `.claude/agents/` (project scope) or `~/.claude/agents/` (user scope). The file contains metadata (YAML frontmatter) describing the agent's name, description, and allowed tools, followed by a prompt that describes its behavior.
- **Invocation**: Agents can be auto-invoked by Claude based on the context of your request, or explicitly called by name. For example, you might direct Claude to "use the code-reviewer agent" for a step in your workflow.
- **Role**: Each agent acts as a domain expert—such as a Python developer, tester, or documentation writer—helping streamline and modularize work.

---

## How to Define a Custom Command

**Custom Commands** in Claude Code are reusable scripts written in Markdown, placed in `.claude/commands/` (project scope) or `~/.claude/commands/` (user scope). Each command automates part (or all) of your workflow, and can accept arguments.

### How Custom Commands Work

- **File Location/Format**: Each file (e.g., `.claude/commands/build-tool.md`) becomes a command (`/build-tool`).
- **Arguments**: Use `$ARGUMENTS` in your script to accept input (e.g., `/build-tool myproject.md` passes `myproject.md` as an argument).
- **Workflow Orchestration**: Commands can invoke multiple agents, coordinate their outputs, and organize multi-step processes.

# Example: Custom Command for Claude Code

Below is a sample custom command Markdown file for Claude Code. This example creates a command that automates designing, developing, and testing a Python CLI tool.

Place this file in your project at `.claude/commands/build-cli-tool.md`:

---

Design, develop, and test a Python CLI utility based on the provided specification.

1. Use the "designer-agent" agent to:
   - Create the technical specification for the CLI tool.
   - Define the required CLI arguments, options, and expected output.

2. Use the "python-developer" agent to:
   - Implement the CLI tool according to the specification.
   - Ensure code is modular, well-documented, and follows best practices.

3. Use the "qa-tester" agent to:
   - Generate and execute unit and integration tests.
   - Summarize the test coverage and report any issues.

If $ARGUMENTS are provided when running the command, pass them as input to all agents.

---

**How to use this command:**

- Save the markdown file in `.claude/commands/build-cli-tool.md`.
- In Claude Code, run:
  `/build-cli-tool`
  or, to specify extra requirements:
  `/build-cli-tool use argparse not click`

This will trigger a multi-step workflow, delegating each task to the specialized agent you define, ensuring consistency and automation for your Python CLI development process.

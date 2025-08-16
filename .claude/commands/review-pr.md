---
description: Comprehensive pull request review with architectural impact and pattern compliance analysis.
---

When user requests pull request review:

Use rapid-context to load the PR changes, description, and related issue context.

Then use graph-builder to analyze how changes affect module dependencies and system architecture.

Then use semantic-search to verify code follows established patterns and find similar implementations for comparison.

Then use context-synthesizer to assess changes against both code patterns and architectural constraints.

Then use code-intelligence to identify potential bugs, suggest improvements, and verify the solution matches learned patterns.

Then use graph-builder again to verify no architectural principles are violated.

Finally use semantic-search to check if similar changes caused issues in the past.

### Pull Request Number
$ARGUMENTS
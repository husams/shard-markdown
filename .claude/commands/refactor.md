--
description: Trigger refactor workflow.
--

When user requests refactoring:

Use rapid-context to load the target module and understand its current state.

Then use graph-builder to identify all dependencies and consumers of the module.

Then use semantic-search to find best practices and refactoring patterns for similar code.

Then use context-synthesizer to create a refactoring plan that considers both patterns and dependencies.

Finally use code-intelligence to execute the refactoring and update the knowledge base.


### User request
$ARGUMENTS
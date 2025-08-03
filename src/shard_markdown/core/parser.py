"""Markdown document parser for AST generation."""

import re
from typing import Dict, List, Optional

import frontmatter
import markdown

from .models import MarkdownAST, MarkdownElement


class MarkdownParser:
    """Markdown document parser with AST generation."""

    def __init__(self) -> None:
        """Initialize parser with markdown processor."""
        self.md = markdown.Markdown(
            extensions=["toc", "codehilite", "fenced_code", "tables", "nl2br"],
            extension_configs={
                "codehilite": {"css_class": "highlight"},
                "toc": {"title": "Table of Contents"},
            },
        )

    def parse(self, content: str) -> MarkdownAST:
        """Parse markdown content and return AST.

        Args:
            content: Raw markdown content

        Returns:
            Parsed markdown AST with hierarchical structure

        Raises:
            ValueError: If content cannot be parsed
        """
        try:
            # Parse frontmatter if present
            post = frontmatter.loads(content)
            markdown_content = post.content
            metadata = dict(post.metadata)

            # Convert to HTML to extract structure
            html = self.md.convert(markdown_content)

            # Extract structural elements
            elements = self._extract_elements(markdown_content)

            # Build hierarchical structure
            root = self._build_hierarchy(elements)

            return MarkdownAST(
                content=markdown_content,
                metadata=metadata,
                root=root,
                html=html,
                toc=getattr(self.md, "toc", ""),
            )

        except Exception as e:
            raise ValueError(f"Failed to parse markdown: {e}")

    def _extract_elements(self, content: str) -> List[MarkdownElement]:  # noqa: C901
        """Extract structural elements from markdown content.

        Args:
            content: Markdown content to parse

        Returns:
            List of markdown elements in document order
        """
        elements = []
        lines = content.split("\n")
        current_text = []
        in_code_block = False
        code_fence_pattern = re.compile(r"^```")

        for line_num, line in enumerate(lines, 1):
            # Handle code blocks
            if code_fence_pattern.match(line):
                if not in_code_block:
                    # Starting code block - save any accumulated text
                    if current_text:
                        text_content = "\n".join(current_text).strip()
                        if text_content:
                            elements.append(
                                MarkdownElement(
                                    type="paragraph",
                                    content=text_content,
                                    level=0,
                                    line_number=line_num - len(current_text),
                                )
                            )
                        current_text = []
                    in_code_block = True
                    current_text.append(line)
                else:
                    # Ending code block
                    current_text.append(line)
                    code_content = "\n".join(current_text)
                    elements.append(
                        MarkdownElement(
                            type="code_block",
                            content=code_content,
                            level=0,
                            line_number=line_num - len(current_text) + 1,
                        )
                    )
                    current_text = []
                    in_code_block = False
                continue

            if in_code_block:
                current_text.append(line)
                continue

            # Handle headers
            header_match = re.match(r"^(#{1,6})\s+(.+)", line)
            if header_match:
                # Save any accumulated text before header
                if current_text:
                    text_content = "\n".join(current_text).strip()
                    if text_content:
                        elements.append(
                            MarkdownElement(
                                type="paragraph",
                                content=text_content,
                                level=0,
                                line_number=line_num - len(current_text),
                            )
                        )
                    current_text = []

                # Create header element
                level = len(header_match.group(1))
                title = header_match.group(2)
                elements.append(
                    MarkdownElement(
                        type="header",
                        content=title,
                        level=level,
                        line_number=line_num,
                    )
                )
                continue

            # Handle lists
            list_match = re.match(r"^(\s*)([-*+]|\d+\.)\s+(.+)", line)
            if list_match:
                indent = len(list_match.group(1))
                marker = list_match.group(2)
                content = list_match.group(3)
                list_type = "ordered" if marker.endswith(".") else "unordered"

                elements.append(
                    MarkdownElement(
                        type="list_item",
                        content=content,
                        level=indent // 2,  # Estimate nesting level
                        line_number=line_num,
                        metadata={"list_type": list_type, "marker": marker},
                    )
                )
                continue

            # Handle tables
            if "|" in line and line.strip():
                elements.append(
                    MarkdownElement(
                        type="table_row",
                        content=line.strip(),
                        level=0,
                        line_number=line_num,
                    )
                )
                continue

            # Accumulate regular text
            current_text.append(line)

        # Add any remaining text
        if current_text:
            text_content = "\n".join(current_text).strip()
            if text_content:
                elements.append(
                    MarkdownElement(
                        type="paragraph",
                        content=text_content,
                        level=0,
                        line_number=len(lines) - len(current_text) + 1,
                    )
                )

        return elements

    def _build_hierarchy(self, elements: List[MarkdownElement]) -> MarkdownElement:
        """Build hierarchical structure from flat element list.

        Args:
            elements: Flat list of markdown elements

        Returns:
            Root element with nested children
        """
        if not elements:
            return MarkdownElement(
                type="document", content="", level=0, line_number=1, children=[]
            )

        # Create document root
        root = MarkdownElement(
            type="document", content="", level=0, line_number=1, children=[]
        )

        # Stack to track current hierarchy path
        header_stack: List[MarkdownElement] = [root]
        current_section = root

        for element in elements:
            if element.type == "header":
                # Find appropriate parent in header hierarchy
                while len(header_stack) > 1 and header_stack[-1].level >= element.level:
                    header_stack.pop()

                # Add header to current parent
                parent = header_stack[-1]
                parent.children.append(element)

                # Update header stack
                header_stack.append(element)
                current_section = element

            else:
                # Add non-header elements to current section
                current_section.children.append(element)

        return root

    def _extract_metadata_from_headers(
        self, root: MarkdownElement
    ) -> Dict[str, Optional[str]]:
        """Extract document metadata from header structure.

        Args:
            root: Root element of document

        Returns:
            Dictionary of extracted metadata
        """
        metadata = {}

        # Find first header as potential title
        for child in root.children:
            if child.type == "header" and child.level == 1:
                metadata["title"] = child.content
                break

        # Count headers by level
        header_counts = {}
        for element in self._flatten_elements(root):
            if element.type == "header":
                level = element.level
                header_counts[level] = header_counts.get(level, 0) + 1

        metadata["header_counts"] = header_counts

        return metadata

    def _flatten_elements(self, element: MarkdownElement) -> List[MarkdownElement]:
        """Flatten hierarchical elements to a list.

        Args:
            element: Root element to flatten

        Returns:
            Flat list of all elements
        """
        result = [element]
        for child in element.children:
            result.extend(self._flatten_elements(child))
        return result

"""Markdown document parser for AST generation."""

import re
from typing import Any

import frontmatter
import markdown
import yaml

from ..utils.logging import get_logger
from .models import MarkdownAST, MarkdownElement


logger = get_logger(__name__)


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
            try:
                post = frontmatter.loads(content)
                markdown_content = post.content
                frontmatter_metadata = dict(post.metadata)
            except (yaml.scanner.ScannerError, yaml.parser.ParserError, Exception):
                # If frontmatter parsing fails, treat entire content as markdown
                logger.debug(
                    "Failed to parse frontmatter, treating entire content as markdown"
                )
                markdown_content = content
                frontmatter_metadata = {}

            # Convert to HTML to extract structure
            html = self.md.convert(markdown_content)

            # Extract structural elements
            elements = self._extract_elements(markdown_content)

            return MarkdownAST(
                elements=elements,
                frontmatter=frontmatter_metadata,
                metadata={"html": html, "toc": getattr(self.md, "toc", "")},
            )

        except (AttributeError, TypeError, UnicodeDecodeError) as e:
            raise ValueError(f"Failed to parse markdown: {e}") from e

    def _extract_elements(self, content: str) -> list[MarkdownElement]:  # noqa: C901
        """Extract structural elements from markdown content.

        Args:
            content: Markdown content to parse

        Returns:
            List of markdown elements in document order
        """
        elements: list[MarkdownElement] = []
        lines = content.split("\n")
        state: dict[str, Any] = {
            "current_text": [],
            "in_code_block": False,
            "line_offset": 0,
        }
        patterns = {
            "code_fence": re.compile(r"^```"),
            "header": re.compile(r"^(#{1,6})\s+(.+)"),
            "list": re.compile(r"^(\s*)([-*+]|\d+\.)\s+(.+)"),
        }

        for line_num, line in enumerate(lines, 1):
            # Handle code blocks
            if patterns["code_fence"].match(line):
                if not state["in_code_block"]:
                    self._save_accumulated_text(elements, state)
                    state["in_code_block"] = True
                    state["current_text"] = [line]
                    state["line_offset"] = line_num
                else:
                    state["current_text"].append(line)
                    self._create_code_block(elements, state)
                    state["current_text"] = []
                    state["in_code_block"] = False
                continue

            if state["in_code_block"]:
                state["current_text"].append(line)
                continue

            # Handle headers
            header_match = patterns["header"].match(line)
            if header_match:
                self._save_accumulated_text(elements, state)
                level, title = len(header_match.group(1)), header_match.group(2)
                elements.append(
                    MarkdownElement(
                        type="header",
                        text=title,
                        level=level,
                        metadata={"line_number": line_num},
                    )
                )
                continue

            # Handle lists
            list_match = patterns["list"].match(line)
            if list_match:
                indent, marker, content_text = list_match.groups()
                list_type = "ordered" if marker.endswith(".") else "unordered"
                elements.append(
                    MarkdownElement(
                        type="list_item",
                        text=content_text,
                        level=len(indent) // 2,
                        metadata={
                            "line_number": line_num,
                            "list_type": list_type,
                            "marker": marker,
                        },
                    )
                )
                continue

            # Handle tables
            if "|" in line and line.strip():
                elements.append(
                    MarkdownElement(
                        type="table_row",
                        text=line.strip(),
                        level=0,
                        metadata={"line_number": line_num},
                    )
                )
                continue

            # Accumulate regular text
            if not state["current_text"]:
                state["line_offset"] = line_num
            state["current_text"].append(line)

        # Add any remaining text
        self._save_accumulated_text(elements, state)
        return elements

    def _save_accumulated_text(
        self, elements: list[MarkdownElement], state: dict[str, Any]
    ) -> None:
        """Save accumulated text as paragraph element."""
        if state["current_text"]:
            text_content = "\n".join(state["current_text"]).strip()
            if text_content:
                elements.append(
                    MarkdownElement(
                        type="paragraph",
                        text=text_content,
                        level=0,
                        metadata={"line_number": state["line_offset"]},
                    )
                )
            state["current_text"] = []

    def _create_code_block(
        self, elements: list[MarkdownElement], state: dict[str, Any]
    ) -> None:
        """Create code block element from accumulated text."""
        code_content = "\n".join(state["current_text"])
        lang = None
        if state["current_text"] and state["current_text"][0].startswith("```"):
            lang_match = state["current_text"][0][3:].strip()
            if lang_match:
                lang = lang_match

        elements.append(
            MarkdownElement(
                type="code_block",
                text=code_content,
                level=0,
                language=lang,
                metadata={"line_number": state["line_offset"]},
            )
        )

    def _extract_metadata_from_headers(
        self, elements: list[MarkdownElement]
    ) -> dict[str, str | None]:
        """Extract document metadata from header structure.

        Args:
            elements: List of markdown elements

        Returns:
            Dictionary of extracted metadata
        """
        metadata: dict[str, str | None] = {}

        # Find first header as potential title
        for element in elements:
            if element.type == "header" and element.level == 1:
                metadata["title"] = element.text
                break

        # Count headers by level
        header_counts: dict[int, int] = {}
        for element in elements:
            if element.type == "header" and element.level is not None:
                level = element.level
                header_counts[level] = header_counts.get(level, 0) + 1

        metadata["header_counts"] = str(header_counts)

        return metadata

    def get_parser_info(self) -> dict[str, Any]:
        """Get information about the parser configuration.

        Returns:
            Dictionary containing parser configuration details
        """
        return {
            "extensions": (
                self.md.treeprocessors.keys()
                if hasattr(self.md, "treeprocessors")
                else []
            ),
            "parser_type": "markdown_parser",
        }

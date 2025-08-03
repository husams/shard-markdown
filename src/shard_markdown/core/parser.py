"""Markdown parsing with AST generation and frontmatter support."""

import re
from typing import Any, Dict, List, Tuple

import frontmatter
import markdown
from markdown.extensions import codehilite, fenced_code, toc

from ..utils.errors import ProcessingError
from ..utils.logging import get_logger
from .models import MarkdownAST, MarkdownElement

logger = get_logger(__name__)


class MarkdownParser:
    """Markdown document parser with AST generation."""

    def __init__(self):
        """Initialize parser with markdown processor."""
        self.md = markdown.Markdown(
            extensions=["toc", "codehilite", "fenced_code", "tables", "nl2br"],
            extension_configs={
                "codehilite": {"css_class": "highlight"},
                "toc": {"anchorlink": True},
            },
        )

    def parse(self, content: str) -> MarkdownAST:
        """Parse markdown content into structured AST.

        Args:
            content: Raw markdown content

        Returns:
            MarkdownAST with structured elements

        Raises:
            ProcessingError: If parsing fails
        """
        try:
            # Extract frontmatter
            doc_frontmatter, content_without_frontmatter = self.extract_frontmatter(
                content
            )

            # Parse elements
            elements = self._parse_elements(content_without_frontmatter)

            # Extract document metadata
            doc_metadata = self._extract_document_metadata(elements, doc_frontmatter)

            return MarkdownAST(
                elements=elements, frontmatter=doc_frontmatter, metadata=doc_metadata
            )

        except Exception as e:
            raise ProcessingError(
                f"Failed to parse markdown content: {str(e)}",
                error_code=1304,
                context={"content_length": len(content)},
                cause=e,
            )

    def extract_frontmatter(self, content: str) -> Tuple[Dict[str, Any], str]:
        """Extract YAML frontmatter from markdown content.

        Args:
            content: Raw markdown content

        Returns:
            Tuple of (frontmatter_dict, content_without_frontmatter)
        """
        try:
            post = frontmatter.loads(content)
            return post.metadata, post.content
        except Exception as e:
            logger.warning(f"Failed to parse frontmatter: {e}")
            return {}, content

    def _parse_elements(self, content: str) -> List[MarkdownElement]:
        """Parse markdown content into structured elements.

        Args:
            content: Markdown content without frontmatter

        Returns:
            List of MarkdownElement objects
        """
        elements = []
        lines = content.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i]

            # Skip empty lines
            if not line.strip():
                i += 1
                continue

            # Check for headers
            if line.startswith("#"):
                element = self._parse_header(line)
                elements.append(element)
                i += 1

            # Check for code blocks
            elif line.strip().startswith("```"):
                element, consumed_lines = self._parse_code_block(lines[i:])
                elements.append(element)
                i += consumed_lines

            # Check for lists
            elif re.match(r"^[\s]*[-*+]\s", line) or re.match(r"^[\s]*\d+\.\s", line):
                element, consumed_lines = self._parse_list(lines[i:])
                elements.append(element)
                i += consumed_lines

            # Default to paragraph
            else:
                element, consumed_lines = self._parse_paragraph(lines[i:])
                elements.append(element)
                i += consumed_lines

        return elements

    def _parse_header(self, line: str) -> MarkdownElement:
        """Parse header line into MarkdownElement.

        Args:
            line: Header line starting with #

        Returns:
            MarkdownElement for header
        """
        # Count heading level
        level = 0
        for char in line:
            if char == "#":
                level += 1
            else:
                break

        # Extract text
        text = line[level:].strip()

        return MarkdownElement(
            type="header", text=text, level=level, metadata={"original_line": line}
        )

    def _parse_code_block(self, lines: List[str]) -> Tuple[MarkdownElement, int]:
        """Parse code block into MarkdownElement.

        Args:
            lines: Lines starting with code block

        Returns:
            Tuple of (MarkdownElement, number_of_lines_consumed)
        """
        first_line = lines[0].strip()
        language = first_line[3:].strip() if len(first_line) > 3 else None

        code_lines = []
        i = 1

        # Find closing ```
        while i < len(lines):
            if lines[i].strip() == "```":
                break
            code_lines.append(lines[i])
            i += 1

        code_content = "\n".join(code_lines)

        return (
            MarkdownElement(
                type="code_block",
                text=code_content,
                language=language,
                metadata={"line_count": len(code_lines)},
            ),
            i + 1,
        )

    def _parse_list(self, lines: List[str]) -> Tuple[MarkdownElement, int]:
        """Parse list into MarkdownElement.

        Args:
            lines: Lines starting with list

        Returns:
            Tuple of (MarkdownElement, number_of_lines_consumed)
        """
        items = []
        i = 0

        while i < len(lines):
            line = lines[i]

            # Check if this is a list item
            if re.match(r"^[\s]*[-*+]\s", line) or re.match(r"^[\s]*\d+\.\s", line):
                # Extract item text
                item_text = re.sub(r"^[\s]*[-*+\d\.]\s*", "", line)
                items.append(item_text)
                i += 1
            elif line.strip() == "":
                # Empty line continues the list
                i += 1
            else:
                # Non-list line ends the list
                break

        list_type = "ordered" if re.match(r"^[\s]*\d+\.", lines[0]) else "unordered"

        return (
            MarkdownElement(
                type="list",
                text="\n".join(items),
                items=items,
                metadata={"list_type": list_type, "item_count": len(items)},
            ),
            i,
        )

    def _parse_paragraph(self, lines: List[str]) -> Tuple[MarkdownElement, int]:
        """Parse paragraph into MarkdownElement.

        Args:
            lines: Lines starting with paragraph

        Returns:
            Tuple of (MarkdownElement, number_of_lines_consumed)
        """
        paragraph_lines = []
        i = 0

        while i < len(lines):
            line = lines[i]

            # Empty line ends paragraph
            if not line.strip():
                break

            # Special markdown elements end paragraph
            if (
                line.startswith("#")
                or line.strip().startswith("```")
                or re.match(r"^[\s]*[-*+]\s", line)
                or re.match(r"^[\s]*\d+\.\s", line)
            ):
                break

            paragraph_lines.append(line)
            i += 1

        paragraph_text = " ".join(line.strip() for line in paragraph_lines)

        return (
            MarkdownElement(
                type="paragraph",
                text=paragraph_text,
                metadata={"line_count": len(paragraph_lines)},
            ),
            i,
        )

    def _extract_document_metadata(
        self, elements: List[MarkdownElement], frontmatter: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract document-level metadata.

        Args:
            elements: Parsed markdown elements
            frontmatter: Frontmatter metadata

        Returns:
            Document metadata dictionary
        """
        metadata = {}

        # Extract title (first header or from frontmatter)
        title = frontmatter.get("title")
        if not title:
            for element in elements:
                if element.type == "header" and element.level == 1:
                    title = element.text
                    break

        if title:
            metadata["title"] = title

        # Extract other common frontmatter fields
        for field in ["author", "date", "tags", "description", "category"]:
            if field in frontmatter:
                metadata[field] = frontmatter[field]

        # Document statistics
        metadata.update(
            {
                "element_count": len(elements),
                "header_count": len([e for e in elements if e.type == "header"]),
                "code_block_count": len(
                    [e for e in elements if e.type == "code_block"]
                ),
                "list_count": len([e for e in elements if e.type == "list"]),
                "paragraph_count": len([e for e in elements if e.type == "paragraph"]),
            }
        )

        return metadata

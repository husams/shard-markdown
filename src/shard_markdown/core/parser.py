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
            frontmatter_metadata = dict(post.metadata)

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

    def _extract_elements(self, content: str) -> List[MarkdownElement]:  # noqa: C901
        """Extract structural elements from markdown content.

        Args:
            content: Markdown content to parse

        Returns:
            List of markdown elements in document order
        """
        elements: List[MarkdownElement] = []
        lines = content.split("\n")
        current_text: List[str] = []
        in_code_block = False
        code_fence_pattern = re.compile(r"^```")
        line_offset = 0

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
                                    text=text_content,
                                    level=0,
                                    metadata={"line_number": line_offset},
                                )
                            )
                        current_text = []
                    in_code_block = True
                    current_text.append(line)
                    line_offset = line_num
                else:
                    # Ending code block
                    current_text.append(line)
                    code_content = "\n".join(current_text)

                    # Extract language from first line
                    lang = None
                    if current_text and current_text[0].startswith("```"):
                        lang_match = current_text[0][3:].strip()
                        if lang_match:
                            lang = lang_match

                    elements.append(
                        MarkdownElement(
                            type="code_block",
                            text=code_content,
                            level=0,
                            language=lang,
                            metadata={"line_number": line_offset},
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
                                text=text_content,
                                level=0,
                                metadata={"line_number": line_offset},
                            )
                        )
                    current_text = []

                # Create header element
                level = len(header_match.group(1))
                title = header_match.group(2)
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
            list_match = re.match(r"^(\s*)([-*+]|\d+\.)\s+(.+)", line)
            if list_match:
                indent = len(list_match.group(1))
                marker = list_match.group(2)
                content_text = list_match.group(3)
                list_type = "ordered" if marker.endswith(".") else "unordered"

                elements.append(
                    MarkdownElement(
                        type="list_item",
                        text=content_text,
                        level=indent // 2,  # Estimate nesting level
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
            if not current_text:
                line_offset = line_num
            current_text.append(line)

        # Add any remaining text
        if current_text:
            text_content = "\n".join(current_text).strip()
            if text_content:
                elements.append(
                    MarkdownElement(
                        type="paragraph",
                        text=text_content,
                        level=0,
                        metadata={"line_number": line_offset},
                    )
                )

        return elements

    def _extract_metadata_from_headers(
        self, elements: List[MarkdownElement]
    ) -> Dict[str, Optional[str]]:
        """Extract document metadata from header structure.

        Args:
            elements: List of markdown elements

        Returns:
            Dictionary of extracted metadata
        """
        metadata: Dict[str, Optional[str]] = {}

        # Find first header as potential title
        for element in elements:
            if element.type == "header" and element.level == 1:
                metadata["title"] = element.text
                break

        # Count headers by level
        header_counts: Dict[int, int] = {}
        for element in elements:
            if element.type == "header" and element.level is not None:
                level = element.level
                header_counts[level] = header_counts.get(level, 0) + 1

        metadata["header_counts"] = str(header_counts)

        return metadata

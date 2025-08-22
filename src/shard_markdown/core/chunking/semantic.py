"""Semantic-based chunking strategy."""

import re

from ..models import DocumentChunk, MarkdownAST
from .base import BaseChunker


class SemanticChunker(BaseChunker):
    """Chunk documents based on semantic coherence."""

    def chunk_document(self, ast: MarkdownAST) -> list[DocumentChunk]:
        """Chunk document based on semantic boundaries.

        This is a simplified semantic chunker that groups related content
        based on structure and topic changes.

        Args:
            ast: Parsed markdown AST

        Returns:
            List of document chunks
        """
        content = ast.content
        if not content:
            return []

        # Extract semantic units (combination of structure and content analysis)
        semantic_units = self._extract_semantic_units(content)
        if not semantic_units:
            return []

        chunks = []
        current_chunk: list[dict] = []
        current_size = 0
        chunk_start = 0

        for unit in semantic_units:
            unit_size = len(unit["content"])

            # Check if adding this unit would exceed chunk size
            if current_size + unit_size > self.settings.chunk_size and current_chunk:
                # Create chunk from accumulated units
                chunk_content = "\n\n".join([u["content"] for u in current_chunk])
                chunk_end = chunk_start + len(chunk_content)

                chunks.append(
                    self._create_chunk(
                        content=chunk_content,
                        start=chunk_start,
                        end=chunk_end,
                        metadata={
                            "chunk_type": "semantic",
                            "topics": self._extract_topics(current_chunk),
                        },
                    )
                )

                # Start new chunk with overlap if semantically related
                if self.settings.chunk_overlap > 0 and self._are_related(
                    current_chunk[-1], unit
                ):
                    # Include last unit as overlap if related
                    current_chunk = [current_chunk[-1], unit]
                    current_size = sum(len(u["content"]) for u in current_chunk)
                    chunk_start = chunk_end - len(current_chunk[0]["content"])
                else:
                    current_chunk = [unit]
                    current_size = unit_size
                    chunk_start = chunk_end
            else:
                current_chunk.append(unit)
                current_size += unit_size

        # Add remaining units as final chunk
        if current_chunk:
            chunk_content = "\n\n".join([u["content"] for u in current_chunk])
            chunks.append(
                self._create_chunk(
                    content=chunk_content,
                    start=chunk_start,
                    end=chunk_start + len(chunk_content),
                    metadata={
                        "chunk_type": "semantic",
                        "topics": self._extract_topics(current_chunk),
                    },
                )
            )

        return chunks

    def _extract_semantic_units(self, content: str) -> list[dict]:
        """Extract semantic units from content.

        Args:
            content: Document content

        Returns:
            List of semantic unit dictionaries
        """
        units = []

        # First, split by headers to get major topic boundaries
        header_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

        sections = []
        last_pos = 0

        for match in header_pattern.finditer(content):
            if match.start() > last_pos:
                # Add content before header
                pre_content = content[last_pos : match.start()].strip()
                if pre_content:
                    sections.append(
                        {"content": pre_content, "type": "content", "level": 0}
                    )

            # Add header and its content
            header_level = len(match.group(1))
            header_title = match.group(2).strip()

            # Find next header or end
            next_match = header_pattern.search(content, match.end())
            section_end = next_match.start() if next_match else len(content)

            section_content = content[match.start() : section_end].strip()
            sections.append(
                {
                    "content": section_content,
                    "type": "section",
                    "level": header_level,
                    "title": header_title,
                }
            )

            last_pos = section_end

        # Add any remaining content
        if last_pos < len(content):
            remaining = content[last_pos:].strip()
            if remaining:
                sections.append({"content": remaining, "type": "content", "level": 0})

        # Now break sections into semantic units based on content patterns
        for section in sections:
            # Split large sections into paragraphs/lists
            content_str = str(section["content"])
            if len(content_str) > self.settings.chunk_size // 2:
                sub_units = self._split_into_semantic_paragraphs(content_str)
                for sub_unit in sub_units:
                    units.append(
                        {
                            "content": sub_unit,
                            "type": section["type"],
                            "level": section.get("level", 0),
                            "title": section.get("title", ""),
                        }
                    )
            else:
                units.append(section)

        return units

    def _split_into_semantic_paragraphs(self, text: str) -> list[str]:
        """Split text into semantically coherent paragraphs.

        Args:
            text: Text to split

        Returns:
            List of semantic paragraphs
        """
        # Split by double newlines first
        paragraphs = text.split("\n\n")

        semantic_units = []
        current_unit: list[str] = []

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # Check if this is a list (starts with -, *, or number)
            is_list = bool(re.match(r"^[\-\*\d+\.]\s", para))

            # Check if this is code block
            is_code = para.startswith("```")

            # Group related content
            if current_unit:
                last_is_list = bool(re.match(r"^[\-\*\d+\.]\s", current_unit[-1]))
                last_is_code = current_unit[-1].startswith("```")

                # Keep lists together, code blocks separate
                if (is_list and last_is_list) or (
                    not is_code
                    and not last_is_code
                    and not is_list
                    and not last_is_list
                ):
                    current_unit.append(para)
                else:
                    # Start new unit
                    semantic_units.append("\n\n".join(current_unit))
                    current_unit = [para]
            else:
                current_unit = [para]

        # Add remaining unit
        if current_unit:
            semantic_units.append("\n\n".join(current_unit))

        return semantic_units

    def _are_related(self, unit1: dict, unit2: dict) -> bool:
        """Check if two units are semantically related.

        Args:
            unit1: First semantic unit
            unit2: Second semantic unit

        Returns:
            True if units are related
        """
        # Simple heuristic: same type and level, or sequential list items
        if unit1["type"] == unit2["type"] and unit1["level"] == unit2["level"]:
            return True

        # Check for common keywords (simplified)
        words1 = set(unit1["content"].lower().split())
        words2 = set(unit2["content"].lower().split())

        # If significant overlap in vocabulary, consider related
        overlap = len(words1 & words2)
        if overlap > min(len(words1), len(words2)) * 0.3:
            return True

        return False

    def _extract_topics(self, units: list[dict]) -> list[str]:
        """Extract main topics from semantic units.

        Args:
            units: List of semantic units

        Returns:
            List of topic keywords
        """
        topics = []

        for unit in units:
            # Extract title if present
            if unit.get("title"):
                topics.append(unit["title"])

            # Extract key phrases (simplified - just looking for capitalized phrases)
            content = unit["content"]
            capitalized = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", content)
            topics.extend(capitalized[:3])  # Limit to top 3 per unit

        # Deduplicate while preserving order
        seen = set()
        unique_topics = []
        for topic in topics:
            if topic not in seen:
                seen.add(topic)
                unique_topics.append(topic)

        return unique_topics[:10]  # Limit total topics

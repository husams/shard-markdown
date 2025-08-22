"""Section-based chunking strategy."""

import re

from ..models import DocumentChunk, MarkdownAST
from .base import BaseChunker


class SectionChunker(BaseChunker):
    """Chunk documents by markdown sections (headers)."""

    def chunk_document(self, ast: MarkdownAST) -> list[DocumentChunk]:
        """Chunk document by sections defined by headers.

        Args:
            ast: Parsed markdown AST

        Returns:
            List of document chunks
        """
        content = ast.content
        if not content:
            return []

        # Find all headers and their positions
        sections = self._extract_sections(content)
        if not sections:
            # If no sections found, treat entire content as one section
            return [
                self._create_chunk(
                    content=content,
                    start=0,
                    end=len(content),
                    metadata={"chunk_type": "section", "section_level": 0},
                )
            ]

        chunks = []

        for i, section in enumerate(sections):
            section_content = section["content"]

            # If section is too large, split it further
            if len(section_content) > self.settings.chunk_size:
                # Split large sections into smaller chunks
                sub_chunks = self._split_large_section(section)
                chunks.extend(sub_chunks)
            else:
                # Check if we should combine with next section
                if i < len(sections) - 1:
                    next_section = sections[i + 1]
                    combined_size = len(section_content) + len(next_section["content"])

                    # If combined size is reasonable, merge sections
                    if combined_size <= self.settings.chunk_size:
                        # This will be handled in next iteration
                        pass

                chunks.append(
                    self._create_chunk(
                        content=section_content,
                        start=section["start"],
                        end=section["end"],
                        metadata={
                            "chunk_type": "section",
                            "section_title": section.get("title", ""),
                            "section_level": section.get("level", 0),
                        },
                    )
                )

        return chunks

    def _extract_sections(self, content: str) -> list[dict]:
        """Extract sections from markdown content.

        Args:
            content: Markdown content

        Returns:
            List of section dictionaries
        """
        # Match markdown headers (# to ######)
        header_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

        sections = []
        last_pos = 0

        for match in header_pattern.finditer(content):
            header_level = len(match.group(1))
            header_title = match.group(2).strip()
            header_start = match.start()

            # If there was content before this header, add it as a section
            if header_start > last_pos:
                pre_content = content[last_pos:header_start].strip()
                if pre_content:
                    sections.append(
                        {
                            "content": pre_content,
                            "start": last_pos,
                            "end": header_start,
                            "title": "Introduction" if last_pos == 0 else "",
                            "level": 0,
                        }
                    )

            # Start new section with this header
            section_start = header_start
            last_pos = match.end()

            # Find the end of this section (next header or end of content)
            next_header = header_pattern.search(content, match.end())
            if next_header:
                section_end = next_header.start()
            else:
                section_end = len(content)

            section_content = content[section_start:section_end].strip()

            sections.append(
                {
                    "content": section_content,
                    "start": section_start,
                    "end": section_end,
                    "title": header_title,
                    "level": header_level,
                }
            )

            last_pos = section_end

        # Add any remaining content
        if last_pos < len(content):
            remaining = content[last_pos:].strip()
            if remaining:
                sections.append(
                    {
                        "content": remaining,
                        "start": last_pos,
                        "end": len(content),
                        "title": "",
                        "level": 0,
                    }
                )

        return sections

    def _split_large_section(self, section: dict) -> list[DocumentChunk]:
        """Split a large section into smaller chunks.

        Args:
            section: Section dictionary

        Returns:
            List of chunks
        """
        content = section["content"]
        chunks = []
        current_pos = 0

        while current_pos < len(content):
            chunk_end = min(current_pos + self.settings.chunk_size, len(content))

            # Try to break at paragraph boundary
            if chunk_end < len(content):
                # Look for double newline
                last_para = content.rfind("\n\n", current_pos, chunk_end)
                if last_para > current_pos:
                    chunk_end = last_para
                else:
                    # Look for single newline
                    last_newline = content.rfind("\n", current_pos, chunk_end)
                    if last_newline > current_pos:
                        chunk_end = last_newline

            chunk_content = content[current_pos:chunk_end].strip()

            if chunk_content:
                chunks.append(
                    self._create_chunk(
                        content=chunk_content,
                        start=section["start"] + current_pos,
                        end=section["start"] + chunk_end,
                        metadata={
                            "chunk_type": "section",
                            "section_title": section.get("title", ""),
                            "section_level": section.get("level", 0),
                            "is_partial": True,
                        },
                    )
                )

            # Add overlap for next chunk
            if self.settings.chunk_overlap > 0 and chunk_end < len(content):
                overlap_start = max(0, chunk_end - self.settings.chunk_overlap)
                current_pos = overlap_start
            else:
                current_pos = chunk_end

        return chunks

"""Optimized semantic chunking with O(n) complexity.

This module provides an optimized version of the semantic chunker that reduces
time complexity from O(n²) to O(n) through caching, pre-compilation, and
intelligent windowing strategies.
"""

import re
from dataclasses import dataclass, field
from math import log
from typing import Optional, Set

from ..models import DocumentChunk, MarkdownAST
from .base import BaseChunker


@dataclass
class SemanticUnit:
    """Represents a semantic unit with cached properties for performance."""
    
    content: str
    unit_type: str
    level: int
    title: str = ""
    _word_set: Optional[Set[str]] = field(default=None, init=False)
    _word_freq: Optional[dict[str, int]] = field(default=None, init=False)
    
    @property
    def word_set(self) -> Set[str]:
        """Lazy-loaded cached word set."""
        if self._word_set is None:
            self._word_set = set(self.content.lower().split())
        return self._word_set
    
    @property 
    def word_frequencies(self) -> dict[str, int]:
        """Lazy-loaded word frequency map."""
        if self._word_freq is None:
            words = self.content.lower().split()
            self._word_freq = {}
            for word in words:
                self._word_freq[word] = self._word_freq.get(word, 0) + 1
        return self._word_freq
    
    @property
    def size(self) -> int:
        """Get unit size in characters."""
        return len(self.content)


class OptimizedSemanticChunker(BaseChunker):
    """Optimized semantic chunker with O(n) average complexity.
    
    Key optimizations:
    - Pre-compiled regex patterns at class level
    - Cached word sets and frequencies in SemanticUnit
    - TF-IDF weighted similarity instead of simple overlap
    - Sliding window approach for relationship detection
    - Single-pass document frequency building
    """
    
    # Class-level compiled patterns for reuse
    HEADER_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
    LIST_PATTERN = re.compile(r"^[\-\*\d+\.]\s")
    CODE_BLOCK_PATTERN = re.compile(r"^```")
    CAPITALIZED_PHRASE_PATTERN = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b")
    
    # Sliding window size for relationship detection
    DEFAULT_WINDOW_SIZE = 5
    
    def __init__(self, settings) -> None:
        """Initialize optimized chunker.
        
        Args:
            settings: Configuration settings
        """
        super().__init__(settings)
        self.window_size = getattr(settings, 'chunk_semantic_window_size', self.DEFAULT_WINDOW_SIZE)
        self._doc_frequencies: dict[str, int] = {}
        self._total_units = 0
    
    def chunk_document(self, ast: MarkdownAST) -> list[DocumentChunk]:
        """Chunk document with optimized O(n) algorithm.
        
        Args:
            ast: Parsed markdown AST
            
        Returns:
            List of document chunks
        """
        content = ast.content
        if not content:
            return []
        
        # Extract semantic units with caching
        semantic_units = self._extract_semantic_units_optimized(content)
        if not semantic_units:
            return []
        
        # Build document frequencies in single pass
        self._build_document_frequencies(semantic_units)
        
        # Create chunks using sliding window approach
        chunks = self._create_chunks_optimized(semantic_units)
        
        return chunks
    
    def _extract_semantic_units_optimized(self, content: str) -> list[SemanticUnit]:
        """Extract semantic units with optimized processing.
        
        Args:
            content: Document content
            
        Returns:
            List of semantic units with cached properties
        """
        units = []
        
        # Find all headers first (single regex execution)
        sections = []
        last_pos = 0
        
        for match in self.HEADER_PATTERN.finditer(content):
            if match.start() > last_pos:
                # Add content before header
                pre_content = content[last_pos:match.start()].strip()
                if pre_content:
                    sections.append({
                        "content": pre_content,
                        "type": "content",
                        "level": 0,
                        "title": ""
                    })
            
            # Add header section
            header_level = len(match.group(1))
            header_title = match.group(2).strip()
            
            # Find next header or end
            next_match = self.HEADER_PATTERN.search(content, match.end())
            section_end = next_match.start() if next_match else len(content)
            
            section_content = content[match.start():section_end].strip()
            sections.append({
                "content": section_content,
                "type": "section",
                "level": header_level,
                "title": header_title
            })
            
            last_pos = section_end
        
        # Add remaining content
        if last_pos < len(content):
            remaining = content[last_pos:].strip()
            if remaining:
                sections.append({
                    "content": remaining,
                    "type": "content",
                    "level": 0,
                    "title": ""
                })
        
        # Convert to SemanticUnit objects with caching
        for section in sections:
            content_str = section["content"]
            
            # Split large sections efficiently
            if len(content_str) > self.settings.chunk_size // 2:
                sub_units = self._split_semantic_paragraphs_optimized(content_str)
                for sub_content in sub_units:
                    units.append(SemanticUnit(
                        content=sub_content,
                        unit_type=section["type"],
                        level=section.get("level", 0),
                        title=section.get("title", "")
                    ))
            else:
                units.append(SemanticUnit(
                    content=content_str,
                    unit_type=section["type"],
                    level=section.get("level", 0),
                    title=section.get("title", "")
                ))
        
        return units
    
    def _split_semantic_paragraphs_optimized(self, text: str) -> list[str]:
        """Split text into semantic paragraphs with pattern caching.
        
        Args:
            text: Text to split
            
        Returns:
            List of semantic paragraph strings
        """
        paragraphs = text.split("\n\n")
        semantic_units = []
        current_unit: list[str] = []
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # Use pre-compiled patterns
            is_list = bool(self.LIST_PATTERN.match(para))
            is_code = bool(self.CODE_BLOCK_PATTERN.match(para))
            
            if current_unit:
                last_is_list = bool(self.LIST_PATTERN.match(current_unit[-1]))
                last_is_code = bool(self.CODE_BLOCK_PATTERN.match(current_unit[-1]))
                
                # Group related content
                if (is_list and last_is_list) or (
                    not is_code and not last_is_code and 
                    not is_list and not last_is_list
                ):
                    current_unit.append(para)
                else:
                    semantic_units.append("\n\n".join(current_unit))
                    current_unit = [para]
            else:
                current_unit = [para]
        
        if current_unit:
            semantic_units.append("\n\n".join(current_unit))
        
        return semantic_units
    
    def _build_document_frequencies(self, units: list[SemanticUnit]) -> None:
        """Build document frequency map in single pass.
        
        Args:
            units: List of semantic units
        """
        self._doc_frequencies.clear()
        self._total_units = len(units)
        
        for unit in units:
            # Use cached word_set property
            for word in unit.word_set:
                self._doc_frequencies[word] = self._doc_frequencies.get(word, 0) + 1
    
    def _calculate_tfidf_similarity(self, unit1: SemanticUnit, unit2: SemanticUnit) -> float:
        """Calculate TF-IDF weighted similarity between units.
        
        Args:
            unit1: First semantic unit
            unit2: Second semantic unit
            
        Returns:
            Similarity score between 0 and 1
        """
        if not self._doc_frequencies or self._total_units == 0:
            # Fallback to simple overlap if no frequency data
            return self._calculate_simple_overlap(unit1, unit2)
        
        # Get word frequencies (cached)
        freq1 = unit1.word_frequencies
        freq2 = unit2.word_frequencies
        
        # Calculate TF-IDF vectors
        tfidf1 = {}
        tfidf2 = {}
        
        for word, count in freq1.items():
            tf = count / len(freq1)
            idf = log(self._total_units / (1 + self._doc_frequencies.get(word, 0)))
            tfidf1[word] = tf * idf
        
        for word, count in freq2.items():
            tf = count / len(freq2)
            idf = log(self._total_units / (1 + self._doc_frequencies.get(word, 0)))
            tfidf2[word] = tf * idf
        
        # Calculate cosine similarity
        common_words = set(tfidf1.keys()) & set(tfidf2.keys())
        if not common_words:
            return 0.0
        
        dot_product = sum(tfidf1[word] * tfidf2[word] for word in common_words)
        norm1 = sum(v * v for v in tfidf1.values()) ** 0.5
        norm2 = sum(v * v for v in tfidf2.values()) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _calculate_simple_overlap(self, unit1: SemanticUnit, unit2: SemanticUnit) -> float:
        """Calculate simple word overlap similarity.
        
        Args:
            unit1: First semantic unit
            unit2: Second semantic unit
            
        Returns:
            Overlap ratio between 0 and 1
        """
        # Use cached word_set property
        words1 = unit1.word_set
        words2 = unit2.word_set
        
        if not words1 or not words2:
            return 0.0
        
        overlap = len(words1 & words2)
        return overlap / min(len(words1), len(words2))
    
    def _are_units_related(self, unit1: SemanticUnit, unit2: SemanticUnit, 
                          threshold: float = 0.3) -> bool:
        """Check if two units are semantically related using optimized similarity.
        
        Args:
            unit1: First semantic unit
            unit2: Second semantic unit
            threshold: Similarity threshold for considering units related
            
        Returns:
            True if units are related
        """
        # Quick checks first (no computation needed)
        if unit1.unit_type == unit2.unit_type and unit1.level == unit2.level:
            return True
        
        # Calculate TF-IDF similarity (uses cached data)
        similarity = self._calculate_tfidf_similarity(unit1, unit2)
        
        return similarity >= threshold
    
    def _create_chunks_optimized(self, units: list[SemanticUnit]) -> list[DocumentChunk]:
        """Create chunks using sliding window approach for O(n) complexity.
        
        Args:
            units: List of semantic units
            
        Returns:
            List of document chunks
        """
        chunks = []
        current_chunk_units: list[SemanticUnit] = []
        current_size = 0
        chunk_start = 0
        
        for i, unit in enumerate(units):
            unit_size = unit.size
            
            # Check if adding this unit would exceed chunk size
            if current_size + unit_size > self.settings.chunk_size and current_chunk_units:
                # Create chunk from accumulated units
                chunk_content = "\n\n".join([u.content for u in current_chunk_units])
                chunk_end = chunk_start + len(chunk_content)
                
                chunks.append(
                    self._create_chunk(
                        content=chunk_content,
                        start=chunk_start,
                        end=chunk_end,
                        metadata={
                            "chunk_type": "semantic_optimized",
                            "topics": self._extract_topics_optimized(current_chunk_units),
                            "algorithm": "tfidf",
                        },
                    )
                )
                
                # Handle overlap with sliding window
                if self.settings.chunk_overlap > 0 and i > 0:
                    # Look back within window to find related units for overlap
                    overlap_units = []
                    window_start = max(0, len(current_chunk_units) - self.window_size)
                    
                    for j in range(window_start, len(current_chunk_units)):
                        if self._are_units_related(current_chunk_units[j], unit):
                            overlap_units.append(current_chunk_units[j])
                    
                    if overlap_units:
                        # Start new chunk with overlap
                        current_chunk_units = overlap_units + [unit]
                        overlap_size = sum(u.size for u in overlap_units)
                        current_size = overlap_size + unit_size
                        chunk_start = chunk_end - overlap_size
                    else:
                        # No related units, start fresh
                        current_chunk_units = [unit]
                        current_size = unit_size
                        chunk_start = chunk_end
                else:
                    # No overlap configured
                    current_chunk_units = [unit]
                    current_size = unit_size
                    chunk_start = chunk_end
            else:
                # Add unit to current chunk
                current_chunk_units.append(unit)
                current_size += unit_size
        
        # Add remaining units as final chunk
        if current_chunk_units:
            chunk_content = "\n\n".join([u.content for u in current_chunk_units])
            chunks.append(
                self._create_chunk(
                    content=chunk_content,
                    start=chunk_start,
                    end=chunk_start + len(chunk_content),
                    metadata={
                        "chunk_type": "semantic_optimized",
                        "topics": self._extract_topics_optimized(current_chunk_units),
                        "algorithm": "tfidf",
                    },
                )
            )
        
        return chunks
    
    def _extract_topics_optimized(self, units: list[SemanticUnit]) -> list[str]:
        """Extract topics from semantic units using cached data.
        
        Args:
            units: List of semantic units
            
        Returns:
            List of topic keywords
        """
        topics = []
        topic_scores: dict[str, float] = {}
        
        for unit in units:
            # Add titles with high score
            if unit.title:
                topic_scores[unit.title] = topic_scores.get(unit.title, 0) + 2.0
            
            # Extract capitalized phrases using pre-compiled pattern
            capitalized = self.CAPITALIZED_PHRASE_PATTERN.findall(unit.content)
            for phrase in capitalized[:5]:  # Limit per unit
                if len(phrase) > 2:  # Filter out single letters
                    topic_scores[phrase] = topic_scores.get(phrase, 0) + 1.0
        
        # Sort by score and return top topics
        sorted_topics = sorted(topic_scores.items(), key=lambda x: x[1], reverse=True)
        topics = [topic for topic, _ in sorted_topics[:10]]
        
        return topics
"""Advanced semantic chunking with NLP capabilities.

This module provides an advanced semantic chunker with optional NLP features
for enhanced semantic understanding. It gracefully degrades when NLP libraries
are not available, falling back to optimized non-NLP methods.
"""

import re
from dataclasses import dataclass, field
from typing import Optional, Set, Any, List, Dict, Tuple

from ..models import DocumentChunk, MarkdownAST
from .semantic_optimized import OptimizedSemanticChunker, SemanticUnit


@dataclass
class AdvancedSemanticUnit(SemanticUnit):
    """Extended semantic unit with NLP features."""
    
    entities: List[Tuple[str, str]] = field(default_factory=list)  # (entity, type)
    embeddings: Optional[Any] = field(default=None)
    continuity_markers: List[str] = field(default_factory=list)
    coreferences: Dict[str, str] = field(default_factory=dict)


class AdvancedSemanticChunker(OptimizedSemanticChunker):
    """Advanced semantic chunker with optional NLP capabilities.
    
    Features when NLP is enabled:
    - Sentence embeddings for true semantic similarity
    - Named entity recognition and tracking
    - Coreference resolution for pronouns
    - Dynamic programming for optimal boundaries
    - Continuity marker detection
    
    Gracefully degrades to optimized chunking when NLP is unavailable.
    """
    
    # Continuity patterns that suggest content should stay together
    CONTINUITY_PATTERNS = [
        r'\b(however|therefore|furthermore|moreover|additionally|consequently)\b',
        r'\b(first|second|third|finally|lastly)\b',
        r'\b(for example|for instance|such as|including)\b',
        r'\b(as mentioned|as discussed|as noted)\b',
        r'\b(this|these|that|those)\s+\w+',
    ]
    
    # Compiled continuity patterns
    CONTINUITY_REGEX = re.compile(
        '|'.join(CONTINUITY_PATTERNS), 
        re.IGNORECASE
    )
    
    def __init__(self, settings, enable_nlp: bool = False) -> None:
        """Initialize advanced chunker with optional NLP.
        
        Args:
            settings: Configuration settings
            enable_nlp: Whether to enable NLP features (requires optional dependencies)
        """
        super().__init__(settings)
        self.nlp_enabled = False
        self.nlp_processor = None
        self.sentence_encoder = None
        
        if enable_nlp:
            self._initialize_nlp()
    
    def _initialize_nlp(self) -> None:
        """Initialize NLP components if available."""
        try:
            # Try to import spaCy for NER and linguistic features
            import spacy
            self.nlp_processor = spacy.load("en_core_web_sm")
            self.nlp_enabled = True
        except (ImportError, OSError):
            # SpaCy not available or model not installed
            pass
        
        try:
            # Try to import sentence-transformers for embeddings
            from sentence_transformers import SentenceTransformer
            self.sentence_encoder = SentenceTransformer('all-MiniLM-L6-v2')
        except ImportError:
            # Sentence-transformers not available
            pass
    
    def chunk_document(self, ast: MarkdownAST) -> list[DocumentChunk]:
        """Chunk document with advanced semantic understanding.
        
        Args:
            ast: Parsed markdown AST
            
        Returns:
            List of document chunks
        """
        content = ast.content
        if not content:
            return []
        
        # Extract semantic units with advanced features
        if self.nlp_enabled:
            semantic_units = self._extract_advanced_units(content)
        else:
            # Fall back to optimized extraction
            basic_units = self._extract_semantic_units_optimized(content)
            semantic_units = [self._upgrade_to_advanced_unit(u) for u in basic_units]
        
        if not semantic_units:
            return []
        
        # Build document frequencies
        self._build_document_frequencies(semantic_units)
        
        # Create chunks with advanced boundary detection
        if self.nlp_enabled:
            chunks = self._create_chunks_with_dynamic_programming(semantic_units)
        else:
            chunks = self._create_chunks_with_continuity(semantic_units)
        
        return chunks
    
    def _upgrade_to_advanced_unit(self, unit: SemanticUnit) -> AdvancedSemanticUnit:
        """Convert basic semantic unit to advanced unit.
        
        Args:
            unit: Basic semantic unit
            
        Returns:
            Advanced semantic unit
        """
        # Detect continuity markers
        continuity_markers = self.CONTINUITY_REGEX.findall(unit.content)
        
        return AdvancedSemanticUnit(
            content=unit.content,
            unit_type=unit.unit_type,
            level=unit.level,
            title=unit.title,
            continuity_markers=continuity_markers
        )
    
    def _extract_advanced_units(self, content: str) -> List[AdvancedSemanticUnit]:
        """Extract semantic units with NLP features.
        
        Args:
            content: Document content
            
        Returns:
            List of advanced semantic units
        """
        # Start with optimized extraction
        basic_units = self._extract_semantic_units_optimized(content)
        advanced_units = []
        
        for unit in basic_units:
            advanced_unit = self._upgrade_to_advanced_unit(unit)
            
            if self.nlp_processor:
                # Process with spaCy for NER and linguistic features
                doc = self.nlp_processor(unit.content)
                
                # Extract named entities
                entities = [(ent.text, ent.label_) for ent in doc.ents]
                advanced_unit.entities = entities
                
                # Simple coreference detection (pronouns to nearest preceding entity)
                coreferences = self._detect_coreferences(doc)
                advanced_unit.coreferences = coreferences
            
            if self.sentence_encoder:
                # Generate embeddings for semantic similarity
                advanced_unit.embeddings = self.sentence_encoder.encode(
                    unit.content, 
                    convert_to_tensor=True
                )
            
            advanced_units.append(advanced_unit)
        
        return advanced_units
    
    def _detect_coreferences(self, doc) -> Dict[str, str]:
        """Simple coreference detection for pronouns.
        
        Args:
            doc: spaCy processed document
            
        Returns:
            Dictionary mapping pronouns to likely referents
        """
        coreferences = {}
        last_person = None
        last_org = None
        last_thing = None
        
        for token in doc:
            # Track entities
            if token.ent_type_ == "PERSON":
                last_person = token.text
            elif token.ent_type_ == "ORG":
                last_org = token.text
            elif token.pos_ == "NOUN" and token.dep_ in ["nsubj", "dobj"]:
                last_thing = token.text
            
            # Map pronouns to likely referents
            if token.pos_ == "PRON":
                if token.text.lower() in ["he", "she", "him", "her"]:
                    if last_person:
                        coreferences[token.text] = last_person
                elif token.text.lower() in ["it", "its"]:
                    if last_thing:
                        coreferences[token.text] = last_thing
                elif token.text.lower() in ["they", "them", "their"]:
                    if last_org:
                        coreferences[token.text] = last_org
        
        return coreferences
    
    def _calculate_advanced_similarity(
        self, 
        unit1: AdvancedSemanticUnit, 
        unit2: AdvancedSemanticUnit
    ) -> float:
        """Calculate similarity using embeddings if available.
        
        Args:
            unit1: First semantic unit
            unit2: Second semantic unit
            
        Returns:
            Similarity score between 0 and 1
        """
        if unit1.embeddings is not None and unit2.embeddings is not None:
            # Use cosine similarity of embeddings
            try:
                from torch.nn.functional import cosine_similarity
                similarity = cosine_similarity(
                    unit1.embeddings.unsqueeze(0),
                    unit2.embeddings.unsqueeze(0)
                ).item()
                return max(0.0, min(1.0, similarity))
            except ImportError:
                pass
        
        # Fall back to TF-IDF similarity
        return self._calculate_tfidf_similarity(unit1, unit2)
    
    def _has_continuity(
        self, 
        unit1: AdvancedSemanticUnit, 
        unit2: AdvancedSemanticUnit
    ) -> bool:
        """Check if unit2 has continuity markers referencing unit1.
        
        Args:
            unit1: First semantic unit
            unit2: Second semantic unit
            
        Returns:
            True if strong continuity detected
        """
        # Check for explicit continuity markers
        if unit2.continuity_markers:
            return True
        
        # Check for entity continuity
        if unit1.entities and unit2.entities:
            entities1 = set(e[0] for e in unit1.entities)
            entities2 = set(e[0] for e in unit2.entities)
            if entities1 & entities2:  # Shared entities
                return True
        
        # Check for coreference chains
        if unit2.coreferences:
            # If unit2 has pronouns referring to entities in unit1
            for pronoun, referent in unit2.coreferences.items():
                if referent in unit1.content:
                    return True
        
        return False
    
    def _create_chunks_with_continuity(
        self, 
        units: List[AdvancedSemanticUnit]
    ) -> List[DocumentChunk]:
        """Create chunks considering continuity markers.
        
        Args:
            units: List of advanced semantic units
            
        Returns:
            List of document chunks
        """
        chunks = []
        current_chunk_units: List[AdvancedSemanticUnit] = []
        current_size = 0
        chunk_start = 0
        
        for i, unit in enumerate(units):
            unit_size = unit.size
            
            # Check if we should keep units together due to continuity
            force_together = False
            if i > 0 and current_chunk_units:
                force_together = self._has_continuity(current_chunk_units[-1], unit)
            
            # Decide whether to create new chunk
            should_split = (
                current_size + unit_size > self.settings.chunk_size 
                and current_chunk_units 
                and not force_together
            )
            
            if should_split:
                # Create chunk from accumulated units
                chunk_content = "\n\n".join([u.content for u in current_chunk_units])
                chunk_end = chunk_start + len(chunk_content)
                
                chunks.append(
                    self._create_chunk(
                        content=chunk_content,
                        start=chunk_start,
                        end=chunk_end,
                        metadata={
                            "chunk_type": "semantic_advanced",
                            "topics": self._extract_topics_advanced(current_chunk_units),
                            "entities": self._extract_entities(current_chunk_units),
                            "algorithm": "advanced_continuity",
                        },
                    )
                )
                
                # Handle overlap with continuity awareness
                if self.settings.chunk_overlap > 0:
                    overlap_units = self._select_overlap_units(
                        current_chunk_units, unit
                    )
                    
                    if overlap_units:
                        current_chunk_units = overlap_units + [unit]
                        overlap_size = sum(u.size for u in overlap_units)
                        current_size = overlap_size + unit_size
                        chunk_start = chunk_end - overlap_size
                    else:
                        current_chunk_units = [unit]
                        current_size = unit_size
                        chunk_start = chunk_end
                else:
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
                        "chunk_type": "semantic_advanced",
                        "topics": self._extract_topics_advanced(current_chunk_units),
                        "entities": self._extract_entities(current_chunk_units),
                        "algorithm": "advanced_continuity",
                    },
                )
            )
        
        return chunks
    
    def _create_chunks_with_dynamic_programming(
        self, 
        units: List[AdvancedSemanticUnit]
    ) -> List[DocumentChunk]:
        """Create chunks using dynamic programming for optimal boundaries.
        
        This method finds the optimal chunking that maximizes semantic coherence
        while respecting size constraints.
        
        Args:
            units: List of advanced semantic units
            
        Returns:
            List of document chunks
        """
        n = len(units)
        if n == 0:
            return []
        
        # Dynamic programming table
        # dp[i] = (min_cost, best_split) for units[0:i]
        dp = [(float('inf'), -1) for _ in range(n + 1)]
        dp[0] = (0, -1)
        
        # Calculate optimal splits
        for i in range(1, n + 1):
            # Try all possible previous split points
            for j in range(max(0, i - 20), i):  # Limit lookback for efficiency
                # Calculate chunk from j to i
                chunk_units = units[j:i]
                chunk_size = sum(u.size for u in chunk_units)
                
                # Skip if chunk is too large
                if chunk_size > self.settings.chunk_size * 1.2:  # Allow 20% overflow
                    continue
                
                # Calculate cost (lower is better)
                cost = self._calculate_chunk_cost(chunk_units)
                
                # Update DP table if this is better
                total_cost = dp[j][0] + cost
                if total_cost < dp[i][0]:
                    dp[i] = (total_cost, j)
        
        # Reconstruct optimal chunking
        chunks = []
        i = n
        boundaries = []
        
        while i > 0:
            prev = dp[i][1]
            if prev >= 0:
                boundaries.append((prev, i))
            i = prev
        
        boundaries.reverse()
        chunk_start = 0
        
        for start_idx, end_idx in boundaries:
            chunk_units = units[start_idx:end_idx]
            chunk_content = "\n\n".join([u.content for u in chunk_units])
            chunk_end = chunk_start + len(chunk_content)
            
            chunks.append(
                self._create_chunk(
                    content=chunk_content,
                    start=chunk_start,
                    end=chunk_end,
                    metadata={
                        "chunk_type": "semantic_advanced",
                        "topics": self._extract_topics_advanced(chunk_units),
                        "entities": self._extract_entities(chunk_units),
                        "algorithm": "dynamic_programming",
                    },
                )
            )
            
            chunk_start = chunk_end
        
        return chunks
    
    def _calculate_chunk_cost(self, units: List[AdvancedSemanticUnit]) -> float:
        """Calculate cost of a chunk (lower is better).
        
        Args:
            units: List of units in the chunk
            
        Returns:
            Cost value
        """
        if not units:
            return float('inf')
        
        # Size penalty
        total_size = sum(u.size for u in units)
        size_penalty = 0
        
        if total_size < self.settings.chunk_size * 0.5:
            # Too small
            size_penalty = (self.settings.chunk_size * 0.5 - total_size) / 100
        elif total_size > self.settings.chunk_size:
            # Too large
            size_penalty = (total_size - self.settings.chunk_size) / 50
        
        # Coherence bonus (negative cost)
        coherence = 0
        for i in range(1, len(units)):
            similarity = self._calculate_advanced_similarity(units[i-1], units[i])
            coherence += similarity
            
            # Bonus for continuity
            if self._has_continuity(units[i-1], units[i]):
                coherence += 0.5
        
        # Boundary penalty for breaking sections
        boundary_penalty = 0
        if len(units) > 1:
            # Penalty for mixing different section levels
            levels = set(u.level for u in units)
            if len(levels) > 1:
                boundary_penalty = len(levels) * 0.2
        
        # Total cost
        cost = size_penalty + boundary_penalty - coherence
        return cost
    
    def _select_overlap_units(
        self, 
        current_units: List[AdvancedSemanticUnit],
        next_unit: AdvancedSemanticUnit
    ) -> List[AdvancedSemanticUnit]:
        """Select units for overlap based on relevance to next unit.
        
        Args:
            current_units: Units in current chunk
            next_unit: First unit of next chunk
            
        Returns:
            Selected units for overlap
        """
        if not current_units:
            return []
        
        # Score each unit by relevance to next unit
        scored_units = []
        for i, unit in enumerate(current_units):
            score = 0
            
            # Recency bonus
            score += (i + 1) / len(current_units)
            
            # Similarity score
            score += self._calculate_advanced_similarity(unit, next_unit) * 2
            
            # Continuity bonus
            if self._has_continuity(unit, next_unit):
                score += 1
            
            scored_units.append((score, unit))
        
        # Sort by score and select top units within overlap limit
        scored_units.sort(reverse=True, key=lambda x: x[0])
        
        overlap_units = []
        overlap_size = 0
        
        for score, unit in scored_units:
            if overlap_size + unit.size <= self.settings.chunk_overlap:
                overlap_units.append(unit)
                overlap_size += unit.size
            elif not overlap_units:
                # Include at least one unit if possible
                overlap_units.append(unit)
                break
        
        # Restore original order
        original_indices = {id(u): i for i, u in enumerate(current_units)}
        overlap_units.sort(key=lambda u: original_indices[id(u)])
        
        return overlap_units
    
    def _extract_topics_advanced(
        self, 
        units: List[AdvancedSemanticUnit]
    ) -> List[str]:
        """Extract topics with entity awareness.
        
        Args:
            units: List of advanced semantic units
            
        Returns:
            List of topic keywords
        """
        # Start with basic topic extraction
        topics = super()._extract_topics_optimized(units)
        
        # Add important entities as topics
        entity_counts: Dict[str, int] = {}
        for unit in units:
            for entity, entity_type in unit.entities:
                if entity_type in ["PERSON", "ORG", "PRODUCT", "WORK_OF_ART"]:
                    entity_counts[entity] = entity_counts.get(entity, 0) + 1
        
        # Add most frequent entities
        top_entities = sorted(
            entity_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:5]
        
        for entity, _ in top_entities:
            if entity not in topics:
                topics.append(entity)
        
        return topics[:15]  # Limit total topics
    
    def _extract_entities(
        self, 
        units: List[AdvancedSemanticUnit]
    ) -> List[Dict[str, str]]:
        """Extract unique entities from units.
        
        Args:
            units: List of advanced semantic units
            
        Returns:
            List of entity dictionaries
        """
        seen = set()
        entities = []
        
        for unit in units:
            for entity_text, entity_type in unit.entities:
                key = (entity_text, entity_type)
                if key not in seen:
                    seen.add(key)
                    entities.append({
                        "text": entity_text,
                        "type": entity_type
                    })
        
        return entities
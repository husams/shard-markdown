"""Patch for Settings class to add semantic chunking algorithm configuration.

This module adds new configuration fields to support the optimized and advanced
semantic chunking algorithms.

To apply this patch, add these fields to the Settings class in settings.py:
"""

# Add these imports at the top of settings.py:
# from typing import Literal

# Add these fields to the Settings class after the existing chunk_* fields:

    # Semantic chunking algorithm configuration
    chunk_semantic_algorithm: str = Field(
        default="original",
        description="Semantic chunking algorithm: 'original', 'optimized', or 'advanced'"
    )
    
    chunk_semantic_window_size: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Window size for semantic similarity comparison in optimized algorithm"
    )
    
    chunk_semantic_enable_nlp: bool = Field(
        default=False,
        description="Enable NLP features in advanced semantic chunking (requires optional dependencies)"
    )
    
    chunk_semantic_similarity_threshold: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Similarity threshold for considering units related (0.0-1.0)"
    )
    
    chunk_semantic_use_tfidf: bool = Field(
        default=True,
        description="Use TF-IDF weighting for similarity calculation in optimized algorithm"
    )
    
    chunk_semantic_max_topics: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of topics to extract per chunk"
    )
    
    # Validation for semantic algorithm field
    @field_validator("chunk_semantic_algorithm")
    @classmethod
    def validate_semantic_algorithm(cls, v: str) -> str:
        """Validate semantic chunking algorithm selection."""
        valid_algorithms = ["original", "optimized", "advanced"]
        if v not in valid_algorithms:
            raise ValueError(
                f"Invalid semantic algorithm: '{v}'. "
                f"Must be one of: {', '.join(valid_algorithms)}"
            )
        return v
    
    @field_validator("chunk_semantic_window_size")
    @classmethod
    def validate_window_size(cls, v: int, info: Any) -> int:
        """Ensure window size is reasonable for performance."""
        if info.data and "chunk_size" in info.data:
            chunk_size = info.data["chunk_size"]
            # Window size should not be too large relative to chunk size
            max_window = min(20, chunk_size // 100)
            if v > max_window:
                raise ValueError(
                    f"Window size {v} is too large for chunk size {chunk_size}. "
                    f"Maximum recommended: {max_window}"
                )
        return v
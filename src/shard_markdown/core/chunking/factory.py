"""Factory for creating appropriate semantic chunker based on configuration.

This module provides a factory function to instantiate the correct semantic
chunker implementation based on the configuration settings.
"""

from typing import Union

from ...config.settings import Settings
from .semantic import SemanticChunker
from .semantic_optimized import OptimizedSemanticChunker
from .semantic_advanced import AdvancedSemanticChunker
from .base import BaseChunker


def create_semantic_chunker(settings: Settings) -> BaseChunker:
    """Create appropriate semantic chunker based on settings.
    
    Args:
        settings: Configuration settings containing algorithm selection
        
    Returns:
        Instance of the selected semantic chunker
        
    Raises:
        ValueError: If unknown algorithm is specified
    """
    # Get algorithm selection from settings (default to original if not set)
    algorithm = getattr(settings, 'chunk_semantic_algorithm', 'original')
    
    if algorithm == 'original':
        return SemanticChunker(settings)
    
    elif algorithm == 'optimized':
        return OptimizedSemanticChunker(settings)
    
    elif algorithm == 'advanced':
        # Check if NLP should be enabled
        enable_nlp = getattr(settings, 'chunk_semantic_enable_nlp', False)
        return AdvancedSemanticChunker(settings, enable_nlp=enable_nlp)
    
    else:
        raise ValueError(
            f"Unknown semantic chunking algorithm: {algorithm}. "
            f"Valid options are: 'original', 'optimized', 'advanced'"
        )


def get_available_algorithms() -> list[str]:
    """Get list of available semantic chunking algorithms.
    
    Returns:
        List of algorithm names
    """
    return ['original', 'optimized', 'advanced']


def get_algorithm_info(algorithm: str) -> dict:
    """Get information about a specific algorithm.
    
    Args:
        algorithm: Algorithm name
        
    Returns:
        Dictionary with algorithm information
        
    Raises:
        ValueError: If unknown algorithm
    """
    info = {
        'original': {
            'name': 'Original Semantic Chunker',
            'description': 'Original implementation with O(n²) complexity',
            'complexity': 'O(n²)',
            'features': ['Basic semantic grouping', 'Topic extraction'],
            'recommended_for': 'Small documents (<50KB)',
            'status': 'stable'
        },
        'optimized': {
            'name': 'Optimized Semantic Chunker',
            'description': 'Performance-optimized with O(n) average complexity',
            'complexity': 'O(n)',
            'features': [
                'Cached word sets',
                'TF-IDF similarity',
                'Sliding window approach',
                'Pre-compiled patterns'
            ],
            'recommended_for': 'Medium to large documents (50KB-5MB)',
            'status': 'stable'
        },
        'advanced': {
            'name': 'Advanced Semantic Chunker',
            'description': 'NLP-enhanced chunker with optional AI features',
            'complexity': 'O(n) to O(n log n)',
            'features': [
                'Sentence embeddings (optional)',
                'Named entity recognition (optional)',
                'Coreference resolution (optional)',
                'Dynamic programming boundaries',
                'Continuity detection'
            ],
            'recommended_for': 'Complex documents requiring deep understanding',
            'status': 'experimental',
            'optional_dependencies': ['spacy', 'sentence-transformers']
        }
    }
    
    if algorithm not in info:
        raise ValueError(f"Unknown algorithm: {algorithm}")
    
    return info[algorithm]


def benchmark_algorithms(content: str, settings: Settings) -> dict:
    """Benchmark different algorithms on the same content.
    
    Args:
        content: Document content to chunk
        settings: Base settings (algorithm will be overridden)
        
    Returns:
        Dictionary with benchmark results for each algorithm
    """
    import time
    from ..models import MarkdownAST, MarkdownElement
    
    # Create simple AST
    ast = MarkdownAST(
        elements=[MarkdownElement(type="document", text=content)]
    )
    
    results = {}
    
    for algorithm in get_available_algorithms():
        # Create settings copy with this algorithm
        test_settings = settings.model_copy()
        
        # Set algorithm (handle case where field doesn't exist)
        if hasattr(test_settings, 'chunk_semantic_algorithm'):
            test_settings.chunk_semantic_algorithm = algorithm
        
        try:
            # Create chunker
            if algorithm == 'original':
                chunker = SemanticChunker(test_settings)
            elif algorithm == 'optimized':
                chunker = OptimizedSemanticChunker(test_settings)
            else:  # advanced
                chunker = AdvancedSemanticChunker(test_settings, enable_nlp=False)
            
            # Measure performance
            start_time = time.perf_counter()
            chunks = chunker.chunk_document(ast)
            end_time = time.perf_counter()
            
            results[algorithm] = {
                'success': True,
                'time': end_time - start_time,
                'chunks': len(chunks),
                'avg_chunk_size': sum(len(c.content) for c in chunks) / len(chunks) if chunks else 0,
                'error': None
            }
            
        except Exception as e:
            results[algorithm] = {
                'success': False,
                'time': None,
                'chunks': 0,
                'avg_chunk_size': 0,
                'error': str(e)
            }
    
    return results


def select_best_algorithm(content_size: int, settings: Settings) -> str:
    """Select the best algorithm based on content size and settings.
    
    Args:
        content_size: Size of content in bytes
        settings: Configuration settings
        
    Returns:
        Recommended algorithm name
    """
    # Check if user has explicitly set an algorithm
    if hasattr(settings, 'chunk_semantic_algorithm'):
        user_choice = settings.chunk_semantic_algorithm
        if user_choice != 'original':
            # Respect user choice if not default
            return user_choice
    
    # Auto-select based on size
    size_kb = content_size / 1024
    
    if size_kb < 50:
        # Small documents - original is fine
        return 'original'
    elif size_kb < 500:
        # Medium documents - optimized is best
        return 'optimized'
    else:
        # Large documents - optimized or advanced
        # Check if NLP dependencies are available
        try:
            import spacy
            import sentence_transformers
            # If available and document is complex, use advanced
            return 'advanced'
        except ImportError:
            # Fall back to optimized
            return 'optimized'
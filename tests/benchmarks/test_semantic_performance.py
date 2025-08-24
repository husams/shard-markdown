"""Performance benchmarks for semantic chunking optimization.

This module tests the performance improvements of the optimized and advanced
semantic chunking algorithms compared to the original implementation.
"""

import time
import random
import string
import pytest
from pathlib import Path
from typing import List, Tuple
import tracemalloc

from shard_markdown.config.settings import Settings
from shard_markdown.core.models import MarkdownAST, MarkdownElement
from shard_markdown.core.chunking.semantic import SemanticChunker
from shard_markdown.core.chunking.semantic_optimized import OptimizedSemanticChunker
from shard_markdown.core.chunking.semantic_advanced import AdvancedSemanticChunker


def generate_test_document(size_kb: int) -> str:
    """Generate a markdown document of specified size.
    
    Args:
        size_kb: Target size in kilobytes
        
    Returns:
        Generated markdown content
    """
    target_bytes = size_kb * 1024
    sections = []
    current_size = 0
    section_num = 1
    
    # Common words for more realistic content
    common_words = [
        "the", "be", "to", "of", "and", "a", "in", "that", "have", "I",
        "it", "for", "not", "on", "with", "he", "as", "you", "do", "at",
        "this", "but", "his", "by", "from", "they", "we", "say", "her", "she",
        "or", "an", "will", "my", "one", "all", "would", "there", "their",
        "what", "so", "up", "out", "if", "about", "who", "get", "which", "go"
    ]
    
    technical_terms = [
        "algorithm", "performance", "optimization", "complexity", "analysis",
        "implementation", "architecture", "design", "pattern", "structure",
        "component", "system", "module", "interface", "abstraction",
        "processing", "computation", "efficiency", "scalability", "throughput"
    ]
    
    while current_size < target_bytes:
        # Generate section header
        section_title = f"Section {section_num}: " + " ".join(
            random.choices(technical_terms, k=random.randint(2, 4))
        ).title()
        
        sections.append(f"\n## {section_title}\n\n")
        current_size += len(sections[-1])
        
        # Generate paragraphs for this section
        paragraphs_in_section = random.randint(3, 8)
        
        for _ in range(paragraphs_in_section):
            if current_size >= target_bytes:
                break
            
            # Generate paragraph
            sentences_in_para = random.randint(3, 6)
            paragraph_sentences = []
            
            for _ in range(sentences_in_para):
                # Generate sentence
                sentence_length = random.randint(10, 25)
                sentence_words = []
                
                # Start with capital
                first_word = random.choice(common_words + technical_terms).capitalize()
                sentence_words.append(first_word)
                
                # Add remaining words
                for _ in range(sentence_length - 1):
                    if random.random() < 0.7:
                        word = random.choice(common_words)
                    else:
                        word = random.choice(technical_terms)
                    sentence_words.append(word)
                
                sentence = " ".join(sentence_words) + "."
                paragraph_sentences.append(sentence)
            
            paragraph = " ".join(paragraph_sentences)
            sections.append(paragraph + "\n\n")
            current_size += len(sections[-1])
        
        # Occasionally add a list
        if random.random() < 0.3 and current_size < target_bytes:
            list_items = random.randint(3, 7)
            for i in range(list_items):
                item_words = random.randint(5, 15)
                item_text = " ".join(random.choices(common_words + technical_terms, k=item_words))
                sections.append(f"- {item_text.capitalize()}\n")
                current_size += len(sections[-1])
            sections.append("\n")
            current_size += 1
        
        # Occasionally add a code block
        if random.random() < 0.2 and current_size < target_bytes:
            code_lines = random.randint(3, 10)
            sections.append("```python\n")
            current_size += len(sections[-1])
            
            for i in range(code_lines):
                indent = "    " if random.random() < 0.3 else ""
                code_content = f"{indent}result_{i} = process_data(input_{i})"
                sections.append(code_content + "\n")
                current_size += len(sections[-1])
            
            sections.append("```\n\n")
            current_size += len(sections[-1])
        
        section_num += 1
    
    return "".join(sections)


def create_test_ast(content: str) -> MarkdownAST:
    """Create a simple AST from markdown content.
    
    Args:
        content: Markdown content
        
    Returns:
        MarkdownAST object
    """
    # Simple parsing - just create one big element
    # In real usage, the parser would create a proper AST
    elements = [
        MarkdownElement(
            type="document",
            text=content
        )
    ]
    
    return MarkdownAST(elements=elements)


@pytest.mark.benchmark
class TestSemanticPerformance:
    """Benchmark tests for semantic chunking performance."""
    
    @pytest.fixture
    def settings(self):
        """Create test settings."""
        return Settings(
            chunk_size=1000,
            chunk_overlap=200,
            chunk_method="semantic"
        )
    
    @pytest.mark.parametrize("size_kb,expected_speedup", [
        (10, 1.1),   # Small document - modest improvement expected
        (50, 1.5),   # Medium document
        (100, 2.0),  # Large document - 2x speedup expected
        (500, 5.0),  # Very large document - significant speedup
    ])
    def test_optimized_performance(self, settings, size_kb, expected_speedup):
        """Test that optimized version meets performance targets.
        
        Args:
            settings: Test settings
            size_kb: Document size in KB
            expected_speedup: Minimum expected speedup factor
        """
        # Generate test document
        content = generate_test_document(size_kb)
        ast = create_test_ast(content)
        
        # Measure original performance
        original_chunker = SemanticChunker(settings)
        start_time = time.perf_counter()
        original_chunks = original_chunker.chunk_document(ast)
        original_time = time.perf_counter() - start_time
        
        # Measure optimized performance
        optimized_chunker = OptimizedSemanticChunker(settings)
        start_time = time.perf_counter()
        optimized_chunks = optimized_chunker.chunk_document(ast)
        optimized_time = time.perf_counter() - start_time
        
        # Calculate speedup
        speedup = original_time / optimized_time if optimized_time > 0 else float('inf')
        
        # Report results
        print(f"\nDocument size: {size_kb}KB")
        print(f"Original time: {original_time:.3f}s")
        print(f"Optimized time: {optimized_time:.3f}s")
        print(f"Speedup: {speedup:.2f}x")
        print(f"Original chunks: {len(original_chunks)}")
        print(f"Optimized chunks: {len(optimized_chunks)}")
        
        # Verify performance improvement
        assert speedup >= expected_speedup * 0.8, (
            f"Expected at least {expected_speedup * 0.8:.1f}x speedup, got {speedup:.2f}x"
        )
        
        # Verify chunk count is similar (within 20%)
        chunk_diff = abs(len(optimized_chunks) - len(original_chunks))
        chunk_ratio = chunk_diff / max(len(original_chunks), 1)
        assert chunk_ratio <= 0.2, (
            f"Chunk count difference too large: {chunk_ratio:.1%}"
        )
    
    def test_linear_scaling(self, settings):
        """Verify O(n) complexity through scaling analysis.
        
        Tests that doubling the input size roughly doubles the processing time
        for the optimized algorithm, confirming linear complexity.
        """
        sizes = [10, 20, 40, 80]
        times = []
        
        optimized_chunker = OptimizedSemanticChunker(settings)
        
        for size_kb in sizes:
            content = generate_test_document(size_kb)
            ast = create_test_ast(content)
            
            # Measure time (average of 3 runs for stability)
            run_times = []
            for _ in range(3):
                start_time = time.perf_counter()
                optimized_chunker.chunk_document(ast)
                run_time = time.perf_counter() - start_time
                run_times.append(run_time)
            
            avg_time = sum(run_times) / len(run_times)
            times.append(avg_time)
            
            print(f"\nSize: {size_kb}KB, Time: {avg_time:.3f}s")
        
        # Check scaling factor
        # For O(n), doubling size should roughly double time
        scaling_factors = []
        for i in range(1, len(times)):
            size_ratio = sizes[i] / sizes[i-1]
            time_ratio = times[i] / times[i-1] if times[i-1] > 0 else 1
            scaling_factors.append(time_ratio / size_ratio)
            
            print(f"Size {sizes[i-1]}KB -> {sizes[i]}KB: "
                  f"size ratio={size_ratio:.1f}, time ratio={time_ratio:.2f}, "
                  f"scaling factor={time_ratio/size_ratio:.2f}")
        
        # Average scaling factor should be close to 1 for O(n)
        avg_scaling = sum(scaling_factors) / len(scaling_factors)
        print(f"\nAverage scaling factor: {avg_scaling:.2f}")
        
        # Allow some variance but should be roughly linear
        assert 0.8 <= avg_scaling <= 1.5, (
            f"Scaling factor {avg_scaling:.2f} indicates non-linear complexity"
        )
    
    def test_memory_efficiency(self, settings):
        """Verify memory usage is reduced or stable.
        
        Compares peak memory usage between original and optimized implementations.
        """
        size_kb = 100
        content = generate_test_document(size_kb)
        ast = create_test_ast(content)
        
        # Measure original memory usage
        original_chunker = SemanticChunker(settings)
        tracemalloc.start()
        original_chunks = original_chunker.chunk_document(ast)
        original_peak = tracemalloc.get_traced_memory()[1]  # Peak memory
        tracemalloc.stop()
        
        # Measure optimized memory usage
        optimized_chunker = OptimizedSemanticChunker(settings)
        tracemalloc.start()
        optimized_chunks = optimized_chunker.chunk_document(ast)
        optimized_peak = tracemalloc.get_traced_memory()[1]  # Peak memory
        tracemalloc.stop()
        
        # Calculate memory reduction
        memory_reduction = (original_peak - optimized_peak) / original_peak * 100
        
        print(f"\nOriginal peak memory: {original_peak / 1024 / 1024:.2f} MB")
        print(f"Optimized peak memory: {optimized_peak / 1024 / 1024:.2f} MB")
        print(f"Memory reduction: {memory_reduction:.1f}%")
        
        # Memory should not increase significantly (allow 10% increase max)
        assert optimized_peak <= original_peak * 1.1, (
            f"Memory usage increased by {(optimized_peak/original_peak - 1)*100:.1f}%"
        )
    
    def test_advanced_features(self, settings):
        """Test advanced semantic chunker features.
        
        Verifies that advanced features work correctly when available.
        """
        size_kb = 50
        content = generate_test_document(size_kb)
        ast = create_test_ast(content)
        
        # Test without NLP (should still work)
        advanced_chunker = AdvancedSemanticChunker(settings, enable_nlp=False)
        start_time = time.perf_counter()
        chunks = advanced_chunker.chunk_document(ast)
        no_nlp_time = time.perf_counter() - start_time
        
        assert len(chunks) > 0, "Advanced chunker should produce chunks"
        
        # Check metadata
        for chunk in chunks:
            assert chunk.metadata.get("chunk_type") == "semantic_advanced"
            assert "algorithm" in chunk.metadata
            assert "topics" in chunk.metadata
        
        print(f"\nAdvanced chunker (no NLP): {no_nlp_time:.3f}s, {len(chunks)} chunks")
        
        # Test with NLP if available
        try:
            advanced_chunker_nlp = AdvancedSemanticChunker(settings, enable_nlp=True)
            start_time = time.perf_counter()
            chunks_nlp = advanced_chunker_nlp.chunk_document(ast)
            nlp_time = time.perf_counter() - start_time
            
            print(f"Advanced chunker (with NLP): {nlp_time:.3f}s, {len(chunks_nlp)} chunks")
            
            # NLP version might have different chunking due to better understanding
            # but should still produce reasonable number of chunks
            assert len(chunks_nlp) > 0
            
            # Check for entity metadata if NLP is enabled
            if advanced_chunker_nlp.nlp_enabled:
                for chunk in chunks_nlp:
                    assert "entities" in chunk.metadata
        except Exception as e:
            print(f"NLP features not available: {e}")
    
    def test_chunk_quality_preservation(self, settings):
        """Ensure optimized chunking maintains quality.
        
        Verifies that chunks have similar characteristics between
        original and optimized versions.
        """
        size_kb = 50
        content = generate_test_document(size_kb)
        ast = create_test_ast(content)
        
        # Get chunks from both implementations
        original_chunker = SemanticChunker(settings)
        original_chunks = original_chunker.chunk_document(ast)
        
        optimized_chunker = OptimizedSemanticChunker(settings)
        optimized_chunks = optimized_chunker.chunk_document(ast)
        
        # Compare chunk characteristics
        original_sizes = [len(chunk.content) for chunk in original_chunks]
        optimized_sizes = [len(chunk.content) for chunk in optimized_chunks]
        
        # Average chunk size should be similar
        original_avg = sum(original_sizes) / len(original_sizes) if original_sizes else 0
        optimized_avg = sum(optimized_sizes) / len(optimized_sizes) if optimized_sizes else 0
        
        size_diff_pct = abs(original_avg - optimized_avg) / max(original_avg, 1) * 100
        
        print(f"\nOriginal avg chunk size: {original_avg:.0f} chars")
        print(f"Optimized avg chunk size: {optimized_avg:.0f} chars")
        print(f"Size difference: {size_diff_pct:.1f}%")
        
        # Average size should be within 20%
        assert size_diff_pct <= 20, (
            f"Average chunk size differs by {size_diff_pct:.1f}%"
        )
        
        # Check that chunks respect size limits
        for chunk in optimized_chunks:
            assert len(chunk.content) <= settings.chunk_size * 1.5, (
                "Chunk exceeds size limit by more than 50%"
            )
        
        # Verify metadata is present
        for chunk in optimized_chunks:
            assert "chunk_type" in chunk.metadata
            assert "topics" in chunk.metadata
            assert chunk.metadata["chunk_type"] == "semantic_optimized"
    
    @pytest.mark.parametrize("algorithm", ["original", "optimized", "advanced"])
    def test_consistency_across_runs(self, settings, algorithm):
        """Ensure consistent output across multiple runs.
        
        Args:
            settings: Test settings
            algorithm: Which algorithm to test
        """
        size_kb = 30
        content = generate_test_document(size_kb)
        ast = create_test_ast(content)
        
        # Select chunker
        if algorithm == "original":
            chunker = SemanticChunker(settings)
        elif algorithm == "optimized":
            chunker = OptimizedSemanticChunker(settings)
        else:
            chunker = AdvancedSemanticChunker(settings, enable_nlp=False)
        
        # Run multiple times
        runs = []
        for _ in range(3):
            chunks = chunker.chunk_document(ast)
            runs.append(chunks)
        
        # Verify consistency
        first_run = runs[0]
        for i, run in enumerate(runs[1:], 1):
            assert len(run) == len(first_run), (
                f"Run {i+1} produced {len(run)} chunks vs {len(first_run)} in first run"
            )
            
            # Check that chunk content is identical
            for j, (chunk1, chunk2) in enumerate(zip(first_run, run)):
                assert chunk1.content == chunk2.content, (
                    f"Chunk {j} differs between runs"
                )
        
        print(f"\n{algorithm.capitalize()} chunker: Consistent across 3 runs")


if __name__ == "__main__":
    # Run a quick benchmark if executed directly
    settings = Settings(chunk_size=1000, chunk_overlap=200, chunk_method="semantic")
    
    for size_kb in [10, 50, 100]:
        print(f"\n{'='*60}")
        print(f"Testing with {size_kb}KB document")
        print('='*60)
        
        content = generate_test_document(size_kb)
        ast = create_test_ast(content)
        
        # Test original
        original = SemanticChunker(settings)
        start = time.perf_counter()
        original_chunks = original.chunk_document(ast)
        original_time = time.perf_counter() - start
        
        # Test optimized
        optimized = OptimizedSemanticChunker(settings)
        start = time.perf_counter()
        optimized_chunks = optimized.chunk_document(ast)
        optimized_time = time.perf_counter() - start
        
        # Test advanced
        advanced = AdvancedSemanticChunker(settings, enable_nlp=False)
        start = time.perf_counter()
        advanced_chunks = advanced.chunk_document(ast)
        advanced_time = time.perf_counter() - start
        
        # Report
        print(f"Original:  {original_time:.3f}s ({len(original_chunks)} chunks)")
        print(f"Optimized: {optimized_time:.3f}s ({len(optimized_chunks)} chunks) "
              f"- {original_time/optimized_time:.2f}x speedup")
        print(f"Advanced:  {advanced_time:.3f}s ({len(advanced_chunks)} chunks) "
              f"- {original_time/advanced_time:.2f}x speedup")
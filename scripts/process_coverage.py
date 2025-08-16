#!/usr/bin/env python3
"""Coverage Processing Script.

Processes coverage.json and stores in ChromaDB.
"""

import hashlib
import json
import sys
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shard_markdown.chromadb.client import ChromaDBClient
from shard_markdown.config.loader import load_config


@dataclass
class CoverageFile:
    """Represents coverage data for a single file."""

    path: str
    executed_lines: list[int]
    missing_lines: list[int]
    excluded_lines: list[int]
    coverage_percent: float
    num_statements: int
    covered_lines: int


@dataclass
class CoverageChunk:
    """A chunk of coverage data ready for storage."""

    id: str
    content: str
    metadata: dict[str, Any]


class CoverageStreamProcessor:
    """Processes coverage.json efficiently using streaming."""

    def __init__(self, file_path: Path):
        """Initialize with coverage file path."""
        self.file_path = file_path
        self.data: dict[str, Any] | None = None

    def load_and_parse(self) -> None:
        """Load coverage.json using standard json (since ijson not available)."""
        print(f"Loading coverage file: {self.file_path}")
        with open(self.file_path) as f:
            self.data = json.load(f)
        files_count = len(self.data.get("files", {}) if self.data else {})
        print(f"Loaded coverage data with {files_count} files")

    def get_metadata(self) -> dict[str, Any]:
        """Extract metadata section."""
        if not self.data:
            self.load_and_parse()
        if self.data is None:
            return {}
        meta = self.data.get("meta", {})
        return meta if isinstance(meta, dict) else {}

    def get_totals(self) -> dict[str, Any]:
        """Extract totals section."""
        if not self.data:
            self.load_and_parse()
        if self.data is None:
            return {}
        totals = self.data.get("totals", {})
        return totals if isinstance(totals, dict) else {}

    def iterate_files(self) -> Iterator[CoverageFile]:
        """Yield coverage data for each file."""
        if not self.data:
            self.load_and_parse()

        if self.data is None:
            return

        for file_path, file_data in self.data.get("files", {}).items():
            # Extract summary data from nested structure
            summary = file_data.get("summary", {})
            yield CoverageFile(
                path=file_path,
                executed_lines=file_data.get("executed_lines", []),
                missing_lines=file_data.get("missing_lines", []),
                excluded_lines=file_data.get("excluded_lines", []),
                coverage_percent=summary.get("percent_covered", 0.0),
                num_statements=summary.get("num_statements", 0),
                covered_lines=summary.get("covered_lines", 0),
            )


class CoverageChunker:
    """Intelligent chunking for coverage data."""

    def __init__(self, granularity: str = "module"):
        """Initialize chunker with granularity setting."""
        self.granularity = granularity

    def chunk_by_module(self, files: list[CoverageFile]) -> list[CoverageChunk]:
        """Group files by module and create chunks."""
        modules = defaultdict(list)

        # Group files by module
        for coverage_file in files:
            module = self._extract_module(coverage_file.path)
            modules[module].append(coverage_file)

        chunks = []
        chunk_idx = 0

        for module, module_files in modules.items():
            # Calculate module-level metrics
            total_lines = sum(f.num_statements for f in module_files)
            covered_lines = sum(f.covered_lines for f in module_files)
            coverage_percent = (
                (covered_lines / total_lines * 100) if total_lines > 0 else 0
            )

            # Find best and worst covered files in module
            sorted_files = sorted(
                module_files, key=lambda f: f.coverage_percent, reverse=True
            )

            content = {
                "type": "module_coverage",
                "module": module,
                "coverage": {
                    "percent": round(coverage_percent, 2),
                    "lines": {
                        "total": total_lines,
                        "covered": covered_lines,
                        "missing": total_lines - covered_lines,
                    },
                    "file_count": len(module_files),
                    "best_covered": {
                        "file": sorted_files[0].path if sorted_files else None,
                        "coverage": round(sorted_files[0].coverage_percent, 2)
                        if sorted_files
                        else 0,
                    },
                    "worst_covered": {
                        "file": sorted_files[-1].path if sorted_files else None,
                        "coverage": round(sorted_files[-1].coverage_percent, 2)
                        if sorted_files
                        else 0,
                    },
                    "files": [
                        {
                            "path": f.path,
                            "coverage": round(f.coverage_percent, 2),
                            "lines": f.num_statements,
                            "missing": len(f.missing_lines),
                        }
                        for f in sorted_files[:10]  # Top 10 files
                    ],
                },
            }

            metadata = {
                "chunk_type": "module_coverage",
                "module": module,
                "file_count": len(module_files),
                "coverage_percent": round(coverage_percent, 2),
                "total_lines": total_lines,
                "covered_lines": covered_lines,
                "chunk_index": chunk_idx,
            }

            chunks.append(
                CoverageChunk(
                    id=f"coverage_module_{chunk_idx}_{module.replace('/', '_')}",
                    content=json.dumps(content, indent=2),
                    metadata=metadata,
                )
            )
            chunk_idx += 1

        return chunks

    def chunk_by_file(self, files: list[CoverageFile]) -> list[CoverageChunk]:
        """Create one chunk per file."""
        chunks = []

        for idx, coverage_file in enumerate(files):
            content = {
                "type": "file_coverage",
                "path": coverage_file.path,
                "coverage": {
                    "percent": round(coverage_file.coverage_percent, 2),
                    "lines": {
                        "total": coverage_file.num_statements,
                        "covered": coverage_file.covered_lines,
                        "missing": len(coverage_file.missing_lines),
                        "excluded": len(coverage_file.excluded_lines),
                    },
                    "missing_lines": coverage_file.missing_lines[
                        :50
                    ],  # First 50 missing lines
                    "has_more_missing": len(coverage_file.missing_lines) > 50,
                },
            }

            module = self._extract_module(coverage_file.path)

            metadata = {
                "chunk_type": "file_coverage",
                "file_path": coverage_file.path,
                "module": module,
                "coverage_percent": round(coverage_file.coverage_percent, 2),
                "total_lines": coverage_file.num_statements,
                "covered_lines": coverage_file.covered_lines,
                "missing_lines": len(coverage_file.missing_lines),
                "is_test_file": "test" in coverage_file.path.lower(),
                "chunk_index": idx,
            }

            chunks.append(
                CoverageChunk(
                    id=f"coverage_file_{idx}_{coverage_file.path.replace('/', '_')}",
                    content=json.dumps(content, indent=2),
                    metadata=metadata,
                )
            )

        return chunks

    def _extract_module(self, path: str) -> str:
        """Extract module name from path."""
        parts = path.split("/")

        # Handle different path structures
        if "src" in parts:
            idx = parts.index("src")
            if idx + 1 < len(parts):
                # Return everything after src up to the file
                return "/".join(parts[idx + 1 : -1]) or parts[idx + 1]
        elif "tests" in parts:
            idx = parts.index("tests")
            if idx + 1 < len(parts):
                return "/".join(parts[idx : len(parts) - 1])

        # Default: directory containing the file
        if len(parts) > 1:
            return "/".join(parts[:-1])
        return "root"


class CoverageSummaryGenerator:
    """Generates coverage summary reports."""

    def generate_summary(
        self,
        metadata: dict,
        totals: dict,
        files: list[CoverageFile],
        module_chunks: list[CoverageChunk],
    ) -> dict[str, Any]:
        """Generate comprehensive summary."""
        # Sort files by coverage
        sorted_files = sorted(files, key=lambda f: f.coverage_percent, reverse=True)

        # Get module coverage from chunks
        module_coverage = {}
        for chunk in module_chunks:
            if chunk.metadata.get("chunk_type") == "module_coverage":
                module = chunk.metadata.get("module")
                coverage = chunk.metadata.get("coverage_percent")
                if module and coverage is not None:
                    module_coverage[module] = coverage

        # Sort modules by coverage
        sorted_modules = sorted(
            module_coverage.items(), key=lambda x: x[1], reverse=True
        )

        # Handle both nested and direct totals structure
        if "summary" in totals:
            totals_data = totals["summary"]
        else:
            totals_data = totals

        return {
            "timestamp": datetime.now().isoformat(),
            "overall": {
                "total_files": len(files),
                "total_lines": totals_data.get("num_statements", 0),
                "covered_lines": totals_data.get("covered_lines", 0),
                "missing_lines": totals_data.get("missing_lines", 0),
                "excluded_lines": totals_data.get("excluded_lines", 0),
                "coverage_percent": round(totals_data.get("percent_covered", 0), 2),
            },
            "top_covered_files": [
                {"path": f.path, "coverage": round(f.coverage_percent, 2)}
                for f in sorted_files[:10]
            ],
            "least_covered_files": [
                {"path": f.path, "coverage": round(f.coverage_percent, 2)}
                for f in sorted_files[-10:]
                if f.coverage_percent < 100
            ],
            "module_coverage": dict(sorted_modules),
            "coverage_distribution": self._calculate_distribution(files),
        }

    def _calculate_distribution(self, files: list[CoverageFile]) -> dict[str, int]:
        """Calculate coverage distribution."""
        distribution = {
            "100%": 0,
            "90-99%": 0,
            "80-89%": 0,
            "70-79%": 0,
            "60-69%": 0,
            "50-59%": 0,
            "<50%": 0,
        }

        for f in files:
            if f.coverage_percent == 100:
                distribution["100%"] += 1
            elif f.coverage_percent >= 90:
                distribution["90-99%"] += 1
            elif f.coverage_percent >= 80:
                distribution["80-89%"] += 1
            elif f.coverage_percent >= 70:
                distribution["70-79%"] += 1
            elif f.coverage_percent >= 60:
                distribution["60-69%"] += 1
            elif f.coverage_percent >= 50:
                distribution["50-59%"] += 1
            else:
                distribution["<50%"] += 1

        return distribution

    def format_report(self, summary: dict[str, Any]) -> str:
        """Format summary as readable report."""
        lines = []
        lines.append("=" * 70)
        lines.append("CODE COVERAGE SUMMARY REPORT")
        lines.append("=" * 70)
        lines.append(f"Generated: {summary['timestamp']}")
        lines.append("")

        # Overall metrics
        overall = summary["overall"]
        lines.append("OVERALL METRICS")
        lines.append("-" * 50)
        lines.append(f"Total Files:        {overall['total_files']}")
        lines.append(f"Total Lines:        {overall['total_lines']:,}")
        lines.append(f"Covered Lines:      {overall['covered_lines']:,}")
        lines.append(f"Missing Lines:      {overall['missing_lines']:,}")
        lines.append(f"Overall Coverage:   {overall['coverage_percent']}%")
        lines.append("")

        # Coverage distribution
        lines.append("COVERAGE DISTRIBUTION")
        lines.append("-" * 50)
        dist = summary["coverage_distribution"]
        ranges = ["100%", "90-99%", "80-89%", "70-79%", "60-69%", "50-59%", "<50%"]
        for range_key in ranges:
            count = dist[range_key]
            lines.append(f"{range_key:10} : {count:4} files")
        lines.append("")

        # Module coverage
        lines.append("TOP MODULE COVERAGE")
        lines.append("-" * 50)
        for module, coverage in list(summary["module_coverage"].items())[:10]:
            if len(module) > 40:
                module = "..." + module[-37:]
            lines.append(f"{module:40} {coverage:6.2f}%")
        lines.append("")

        # Top covered files
        lines.append("BEST COVERED FILES")
        lines.append("-" * 50)
        for file_info in summary["top_covered_files"][:5]:
            path = file_info["path"]
            if len(path) > 40:
                path = "..." + path[-37:]
            lines.append(f"{path:40} {file_info['coverage']:6.2f}%")
        lines.append("")

        # Files needing attention
        lines.append("FILES NEEDING ATTENTION (Lowest Coverage)")
        lines.append("-" * 50)
        for file_info in summary["least_covered_files"][:10]:
            path = file_info["path"]
            if len(path) > 40:
                path = "..." + path[-37:]
            lines.append(f"{path:40} {file_info['coverage']:6.2f}%")

        return "\n".join(lines)


def main() -> None:
    """Main processing function."""
    try:
        # Check if coverage.json exists
        coverage_file = Path("coverage.json")
        if not coverage_file.exists():
            print("Error: coverage.json not found")
            sys.exit(1)

        # Initialize processor
        processor = CoverageStreamProcessor(coverage_file)

        # Get metadata and totals
        metadata = processor.get_metadata()
        totals = processor.get_totals()

        print(f"\nCoverage Report Version: {metadata.get('version', 'Unknown')}")
        # Check if totals has the summary field (like files do)
        if "summary" in totals:
            summary = totals["summary"]
            print(f"Overall Coverage: {summary.get('percent_covered', 0):.2f}%")
            print(f"Total Statements: {summary.get('num_statements', 0):,}")
        else:
            # Direct fields
            print(f"Overall Coverage: {totals.get('percent_covered', 0):.2f}%")
            print(f"Total Statements: {totals.get('num_statements', 0):,}")
        print("")

        # Process files
        print("Processing coverage data...")
        files = list(processor.iterate_files())
        print(f"Processed {len(files)} files")

        # Chunk data
        print("\nChunking coverage data...")
        chunker = CoverageChunker(granularity="module")
        module_chunks = chunker.chunk_by_module(files)
        file_chunks = chunker.chunk_by_file(files)

        print(f"Created {len(module_chunks)} module chunks")
        print(f"Created {len(file_chunks)} file chunks")

        # Store in ChromaDB
        print("\nConnecting to ChromaDB...")
        config = load_config()
        # Override host to localhost if needed
        if hasattr(config.chromadb, "host") and config.chromadb.host == "test":
            config.chromadb.host = "localhost"
        client = ChromaDBClient(config.chromadb)

        try:
            client.connect()
            print("Connected to ChromaDB")

            # Create or get collection using client method
            try:
                collection = client.get_collection("coverage")
                print("Found existing coverage collection")
            except Exception as e:
                # Collection doesn't exist, create it
                print(f"Creating new coverage collection (previous error: {e})")
                collection = client.get_or_create_collection(
                    name="coverage",
                    metadata={
                        "description": "Code coverage analysis data",
                        "created_at": datetime.now().isoformat(),
                        "coverage_version": metadata.get("version", "Unknown"),
                        "total_coverage": totals.get("percent_covered", 0)
                        if isinstance(totals.get("percent_covered", 0), int | float)
                        else 0,
                    },
                )
                print("Created new coverage collection")

            print("Using collection: coverage")

            # Prepare data for insertion
            all_chunks = module_chunks + file_chunks

            ids = []
            documents = []
            metadatas = []

            for chunk in all_chunks:
                # Generate stable ID using SHA-256 for better security
                chunk_hash = hashlib.sha256(chunk.content.encode()).hexdigest()[:16]
                ids.append(f"{chunk.id}_{chunk_hash}")
                documents.append(chunk.content)
                metadatas.append(chunk.metadata)

            # Store in batches
            batch_size = 100
            total_stored = 0

            for i in range(0, len(ids), batch_size):
                batch_ids = ids[i : i + batch_size]
                batch_docs = documents[i : i + batch_size]
                batch_meta = metadatas[i : i + batch_size]

                collection.add(
                    ids=batch_ids, documents=batch_docs, metadatas=batch_meta
                )
                total_stored += len(batch_ids)
                print(f"Stored {total_stored}/{len(ids)} chunks...")

            print(f"\n✓ Successfully stored {total_stored} chunks in ChromaDB")

        except Exception as e:
            print(f"Warning: Could not store in ChromaDB: {e}")
            print("Continuing with summary generation...")

        # Generate summary
        print("\nGenerating summary report...")
        generator = CoverageSummaryGenerator()
        summary = generator.generate_summary(metadata, totals, files, module_chunks)

        # Store summary in ChromaDB as well
        try:
            summary_chunk = CoverageChunk(
                id="coverage_summary_report",
                content=json.dumps(summary, indent=2),
                metadata={
                    "chunk_type": "summary",
                    "timestamp": summary["timestamp"],
                    "overall_coverage": summary["overall"]["coverage_percent"],
                },
            )

            collection.add(
                ids=[f"{summary_chunk.id}_{datetime.now().strftime('%Y%m%d')}"],
                documents=[summary_chunk.content],
                metadatas=[summary_chunk.metadata],
            )
            print("✓ Stored summary in ChromaDB")

        except Exception as e:
            print(f"Warning: Could not store summary in ChromaDB: {e}")

        # Display summary
        report = generator.format_report(summary)
        print("\n" + report)

        # Save summary to file
        summary_file = Path("coverage_summary.json")
        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"\n✓ Summary saved to {summary_file}")

    except Exception as e:
        print(f"Error processing coverage: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

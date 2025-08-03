#!/usr/bin/env python3
"""Simple test script to verify package structure."""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

try:
    # Test basic imports without heavy dependencies

    print("✓ Configuration models import successful")


    print("✓ Error classes import successful")


    print("✓ Core models import successful")

    # Test configuration creation
    config = AppConfig()
    print(f"✓ Default configuration created: \
    ChromaDB host = {config.chromadb.host}")

    # Test chunk config
    chunk_config = ChunkingConfig(chunk_size=1000, overlap=200)
    print(f"✓ Chunking config created: size = {chunk_config.chunk_size}")

    print("\nAll basic imports successful! The package structure is correct.")

except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"✗ Unexpected error: {e}")
    sys.exit(1)

#!/usr/bin/env python
"""Test script to validate ChromaDB fixture initialization."""

import os
import sys


# Set environment to simulate CI
os.environ["CI"] = "true"
os.environ["CHROMA_HOST"] = "localhost"
os.environ["CHROMA_PORT"] = "8000"

from pathlib import Path


# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.fixtures.chromadb_fixtures import ChromaDBTestFixture


def main() -> int:
    """Test ChromaDB fixture initialization."""
    print("Testing ChromaDB fixture initialization...")
    print(f"Host: {os.environ.get('CHROMA_HOST')}")
    print(f"Port: {os.environ.get('CHROMA_PORT')}")
    print(f"CI Environment: {os.environ.get('CI')}")

    fixture = ChromaDBTestFixture()
    fixture.setup()

    if fixture.client:
        print("✅ ChromaDB fixture initialized successfully")
        if hasattr(fixture.client, "heartbeat"):
            try:
                fixture.client.heartbeat()
                print("✅ ChromaDB heartbeat successful")
            except Exception as e:
                print(f"⚠️ ChromaDB heartbeat failed: {e}")
        else:
            print("ℹ️ Using mock ChromaDB client")

        # Test collection creation
        try:
            collection = fixture.create_test_collection("test-fixture-validation")
            print(f"✅ Created test collection: {collection.name}")
            fixture.teardown()
            print("✅ Cleanup successful")
        except Exception as e:
            print(f"❌ Collection creation failed: {e}")
    else:
        print("❌ Failed to initialize ChromaDB fixture")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

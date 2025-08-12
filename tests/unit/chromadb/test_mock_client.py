import unittest
from pathlib import Path
import shutil
from unittest.mock import patch

from shard_markdown.chromadb.mock_client import (
    MockChromaDBClient,
    MockCollection,
    create_mock_client,
)
from shard_markdown.config.settings import ChromaDBConfig
from shard_markdown.core.models import DocumentChunk


class TestMockChromaDBClient(unittest.TestCase):
    def setUp(self):
        self.client = MockChromaDBClient()

    def tearDown(self):
        # Explicitly delete the client to trigger cleanup
        temp_dir = self.client._temp_dir
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        del self.client

    def test_initialization_and_cleanup(self):
        """Test that the mock client initializes correctly and cleans up its temp dir."""
        client = MockChromaDBClient()
        temp_dir = client._temp_dir

        self.assertIsInstance(client.config, ChromaDBConfig)
        self.assertTrue(temp_dir.exists())
        self.assertTrue(temp_dir.is_dir())

        temp_dir_path = str(temp_dir)
        del client
        self.assertFalse(Path(temp_dir_path).exists())

    def test_initialization_with_config(self):
        """Test that the mock client can be initialized with a config."""
        config = ChromaDBConfig(host="localhost", port=1234)
        client = MockChromaDBClient(config=config)
        self.assertEqual(client.config.host, "localhost")
        self.assertEqual(client.config.port, 1234)

    def test_create_collection(self):
        """Test creating a collection."""
        collection = self.client.create_collection("test_collection")
        self.assertIsInstance(collection, MockCollection)
        self.assertEqual(collection.name, "test_collection")
        self.assertIn("test_collection", self.client.collections)

    def test_create_duplicate_collection_raises_error(self):
        """Test that creating a duplicate collection raises a ValueError."""
        self.client.create_collection("test_collection")
        with self.assertRaises(ValueError):
            self.client.create_collection("test_collection")

    def test_get_collection(self):
        """Test getting an existing collection."""
        self.client.create_collection("test_collection")
        collection = self.client.get_collection("test_collection")
        self.assertIsInstance(collection, MockCollection)
        self.assertEqual(collection.name, "test_collection")

    def test_get_nonexistent_collection_raises_error(self):
        """Test that getting a non-existent collection raises a ValueError."""
        with self.assertRaises(ValueError):
            self.client.get_collection("nonexistent_collection")

    def test_get_or_create_collection_gets_existing(self):
        """Test that get_or_create_collection returns an existing collection."""
        self.client.create_collection("test_collection")
        collection = self.client.get_or_create_collection("test_collection")
        self.assertEqual(len(self.client.collections), 1)
        self.assertEqual(collection.name, "test_collection")

    def test_get_or_create_collection_creates_new(self):
        """Test that get_or_create_collection creates a new collection if it doesn't exist."""
        collection = self.client.get_or_create_collection(
            "new_collection", create_if_missing=True
        )
        self.assertEqual(len(self.client.collections), 1)
        self.assertEqual(collection.name, "new_collection")

    def test_get_or_create_collection_raises_error_if_not_create(self):
        """Test get_or_create raises error if collection is missing and create_if_missing is False."""
        with self.assertRaises(ValueError):
            self.client.get_or_create_collection(
                "missing_collection", create_if_missing=False
            )

    def test_list_collections(self):
        """Test listing collections."""
        self.assertEqual(self.client.list_collections(), [])
        self.client.create_collection("collection1", metadata={"a": 1})
        self.client.create_collection("collection2", metadata={"b": 2})
        collections = self.client.list_collections()
        self.assertEqual(len(collections), 2)
        # Order is not guaranteed, so we check the names
        names = {c["name"] for c in collections}
        self.assertEqual(names, {"collection1", "collection2"})

    def test_delete_collection(self):
        """Test deleting a collection."""
        self.client.create_collection("test_collection")
        self.assertTrue(self.client.delete_collection("test_collection"))
        self.assertNotIn("test_collection", self.client.collections)

    def test_delete_nonexistent_collection(self):
        """Test that deleting a non-existent collection returns False."""
        self.assertFalse(self.client.delete_collection("nonexistent_collection"))

    def test_bulk_insert_empty(self):
        """Test bulk insert with an empty list of chunks."""
        collection = self.client.create_collection("test_collection")
        result = self.client.bulk_insert(collection, [])
        self.assertTrue(result.success)
        self.assertEqual(result.chunks_inserted, 0)

    def test_bulk_insert_small_batch(self):
        """Test bulk insert with a small batch of chunks."""
        collection = self.client.create_collection("test_collection")
        chunks = [
            DocumentChunk(id=f"chunk_{i}", content=f"content_{i}", metadata={})
            for i in range(10)
        ]
        result = self.client.bulk_insert(collection, chunks)
        self.assertTrue(result.success)
        self.assertEqual(result.chunks_inserted, 10)
        self.assertEqual(collection.count(), 10)

    def test_bulk_insert_large_batch(self):
        """Test bulk insert with a large batch that requires multiple batches."""
        collection = self.client.create_collection("test_collection")
        chunks = [
            DocumentChunk(id=f"chunk_{i}", content=f"content_{i}", metadata={})
            for i in range(150)
        ]
        result = self.client.bulk_insert(collection, chunks)
        self.assertTrue(result.success)
        self.assertEqual(result.chunks_inserted, 150)
        self.assertEqual(collection.count(), 150)

    def test_bulk_insert_failure(self):
        """Test that bulk_insert handles exceptions gracefully."""
        collection = self.client.create_collection("test_collection")
        # To cause a failure, we can mock the `add` method of the collection
        original_add = collection.add
        def failing_add(*args, **kwargs):
            raise RuntimeError("Test exception")
        collection.add = failing_add

        chunks = [DocumentChunk(id="chunk_1", content="content_1", metadata={})]
        result = self.client.bulk_insert(collection, chunks)

        self.assertFalse(result.success)
        self.assertEqual(result.chunks_inserted, 0)
        self.assertIn("Test exception", result.error)

        # Restore original method
        collection.add = original_add

    @patch("shard_markdown.chromadb.mock_client.MockChromaDBClient._save_storage")
    def test_save_storage_called_on_create(self, mock_save_storage):
        """Test that _save_storage is called when a collection is created."""
        self.client.create_collection("new_one")
        mock_save_storage.assert_called_once()

    @patch("shard_markdown.chromadb.mock_client.MockChromaDBClient._save_storage")
    def test_save_storage_called_on_delete(self, mock_save_storage):
        """Test that _save_storage is called when a collection is deleted."""
        self.client.create_collection("to_delete")
        mock_save_storage.reset_mock()  # Reset after creation
        self.client.delete_collection("to_delete")
        mock_save_storage.assert_called_once()

    def test_persistence_across_instances(self):
        """Test that data persists between client instances."""
        # Client 1 creates data and its __del__ will be called by tearDown
        collection1 = self.client.create_collection("persistent_collection")
        chunks = [DocumentChunk(id="p1", content="persistent content", metadata={})]
        self.client.bulk_insert(collection1, chunks)

        # The storage file should now exist
        self.assertTrue(self.client.storage_path.exists())

        # Client 2 should load the data saved by client 1
        client2 = MockChromaDBClient()

        self.assertIn("persistent_collection", client2.collections)
        collection2 = client2.get_collection("persistent_collection")
        self.assertEqual(collection2.count(), 1)
        self.assertEqual(collection2.get(ids=["p1"])["documents"][0], "persistent content")

        # Cleanup for client2
        del client2


if __name__ == "__main__":
    unittest.main()


class TestMockCollection(unittest.TestCase):
    def setUp(self):
        self.collection = MockCollection("test_collection", metadata={"source": "test"})

    def test_add_and_count(self):
        """Test adding documents and getting the count."""
        self.assertEqual(self.collection.count(), 0)
        self.collection.add(
            ids=["1", "2"],
            documents=["doc1", "doc2"],
            metadatas=[{"page": 1}, {"page": 2}],
        )
        self.assertEqual(self.collection.count(), 2)
        self.assertIn("1", self.collection.documents)
        self.assertEqual(self.collection.documents["2"]["document"], "doc2")

    def test_get_all(self):
        """Test getting all documents from a collection."""
        self.collection.add(
            ids=["1", "2"],
            documents=["doc1", "doc2"],
            metadatas=[{"page": 1}, {"page": 2}],
        )
        data = self.collection.get()
        self.assertEqual(len(data["ids"]), 2)
        self.assertIn("1", data["ids"])
        self.assertIn("doc2", data["documents"])

    def test_get_by_ids(self):
        """Test getting documents by their IDs."""
        self.collection.add(
            ids=["1", "2", "3"],
            documents=["doc1", "doc2", "doc3"],
            metadatas=[{"page": 1}, {"page": 2}, {"page": 3}],
        )
        data = self.collection.get(ids=["1", "3"])
        self.assertEqual(data["ids"], ["1", "3"])
        self.assertEqual(data["documents"], ["doc1", "doc3"])
        self.assertEqual(data["metadatas"], [{"page": 1}, {"page": 3}])

    def test_query(self):
        """Test querying the collection."""
        self.collection.add(
            ids=["1", "2"],
            documents=["doc1", "doc2"],
            metadatas=[{"page": 1}, {"page": 2}],
        )
        results = self.collection.query(query_texts=["find me"], n_results=1)
        self.assertEqual(len(results["ids"][0]), 1)
        # The mock query is simple and just returns the first n documents
        self.assertEqual(results["ids"][0][0], "1")

    def test_query_with_metadata_filter(self):
        """Test querying with a metadata filter."""
        self.collection.add(
            ids=["1", "2", "3"],
            documents=["doc1", "doc2", "doc3"],
            metadatas=[
                {"page": 1, "author": "Alice"},
                {"page": 2, "author": "Bob"},
                {"page": 3, "author": "Alice"},
            ],
        )
        results = self.collection.query(
            query_texts=["find alice"], where={"author": "Alice"}
        )
        self.assertEqual(len(results["ids"][0]), 2)
        self.assertIn("1", results["ids"][0])
        self.assertIn("3", results["ids"][0])

    def test_query_with_metadata_filter_no_match(self):
        """Test querying with a metadata filter that has no matches."""
        self.collection.add(
            ids=["1"], documents=["doc1"], metadatas=[{"author": "Alice"}]
        )
        results = self.collection.query(
            query_texts=["find charlie"], where={"author": "Charlie"}
        )
        self.assertEqual(len(results["ids"][0]), 0)


class TestFactoryFunction(unittest.TestCase):
    def test_create_mock_client(self):
        """Test that the factory function returns a MockChromaDBClient instance."""
        client = create_mock_client()
        self.assertIsInstance(client, MockChromaDBClient)
        # Cleanup
        del client

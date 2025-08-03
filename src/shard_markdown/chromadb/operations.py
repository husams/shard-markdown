"""ChromaDB query and retrieval operations."""

from typing import Any, Dict, List, Optional

from ..utils.errors import ChromaDBError
from ..utils.logging import get_logger
from .client import ChromaDBClient

logger = get_logger(__name__)


class ChromaDBOperations:
    """High-level ChromaDB operations for querying and retrieval."""

    def __init__(self, client: ChromaDBClient):
        """Initialize operations handler.

        Args:
            client: ChromaDB client instance
        """
        self.client = client

    def query_collection(
        self,
        collection_name: str,
        query_text: str,
        limit: int = 10,
        similarity_threshold: float = 0.0,
        include_metadata: bool = True,
    ) -> Dict[str, Any]:
        """Query collection for similar documents.

        Args:
            collection_name: Name of collection to query
            query_text: Query text for similarity search
            limit: Maximum number of results to return
            similarity_threshold: Minimum similarity score
            include_metadata: Whether to include metadata in results

        Returns:
            Dictionary with query results

        Raises:
            ChromaDBError: If query fails
        """
        if not self.client._connection_validated:
            raise ChromaDBError(
                "ChromaDB connection not established",
                error_code=1400,
                context={"operation": "query_collection"},
            )

        try:
            collection = self.client.client.get_collection(collection_name)

            # Prepare include list
            include = ["documents", "distances"]
            if include_metadata:
                include.append("metadatas")

            # Perform query
            results = collection.query(
                query_texts=[query_text], n_results=limit, include=include
            )

            # Process results
            processed_results = self._process_query_results(
                results, similarity_threshold, include_metadata
            )

            logger.info(
                f"Query returned {len(processed_results['results'])} results "
                f"from '{collection_name}'"
            )

            return {
                "collection_name": collection_name,
                "query": query_text,
                "total_results": len(processed_results["results"]),
                "similarity_threshold": similarity_threshold,
                "results": processed_results["results"],
            }

        except Exception as e:
            if isinstance(e, ChromaDBError):
                raise

            raise ChromaDBError(
                f"Failed to query collection: {collection_name}",
                error_code=1440,
                context={
                    "collection_name": collection_name,
                    "query": query_text,
                },
                cause=e,
            )

    def get_document(
        self,
        collection_name: str,
        document_id: str,
        include_metadata: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Get specific document by ID.

        Args:
            collection_name: Name of collection
            document_id: Document ID to retrieve
            include_metadata: Whether to include metadata

        Returns:
            Document data or None if not found

        Raises:
            ChromaDBError: If retrieval fails
        """
        if not self.client._connection_validated:
            raise ChromaDBError(
                "ChromaDB connection not established",
                error_code=1400,
                context={"operation": "get_document"},
            )

        try:
            collection = self.client.client.get_collection(collection_name)

            # Prepare include list
            include = ["documents"]
            if include_metadata:
                include.append("metadatas")

            # Get document
            results = collection.get(ids=[document_id], include=include)

            if not results["ids"]:
                return None

            # Format result
            document_data = {
                "id": results["ids"][0],
                "content": results["documents"][0],
            }

            if include_metadata and results.get("metadatas"):
                document_data["metadata"] = results["metadatas"][0]

            logger.info(
                f"Retrieved document '{document_id}' from '{collection_name}'"
            )

            return document_data

        except Exception as e:
            if isinstance(e, ChromaDBError):
                raise

            raise ChromaDBError(
                f"Failed to get document: {document_id}",
                error_code=1441,
                context={
                    "collection_name": collection_name,
                    "document_id": document_id,
                },
                cause=e,
            )

    def list_documents(
        self,
        collection_name: str,
        limit: int = 100,
        offset: int = 0,
        include_metadata: bool = False,
    ) -> Dict[str, Any]:
        """List documents in collection.

        Args:
            collection_name: Name of collection
            limit: Maximum number of documents to return
            offset: Number of documents to skip
            include_metadata: Whether to include metadata

        Returns:
            Dictionary with document list

        Raises:
            ChromaDBError: If listing fails
        """
        if not self.client._connection_validated:
            raise ChromaDBError(
                "ChromaDB connection not established",
                error_code=1400,
                context={"operation": "list_documents"},
            )

        try:
            collection = self.client.client.get_collection(collection_name)

            # Prepare include list
            include = ["documents"]
            if include_metadata:
                include.append("metadatas")

            # Get documents
            results = collection.get(
                limit=limit, offset=offset, include=include
            )

            # Format results
            documents = []
            for i, doc_id in enumerate(results["ids"]):
                doc_data = {
                    "id": doc_id,
                    "content": (
                        results["documents"][i][:200] + "..."
                        if len(results["documents"][i]) > 200
                        else results["documents"][i]
                    ),
                    "content_length": len(results["documents"][i]),
                }

                if include_metadata and results.get("metadatas"):
                    doc_data["metadata"] = results["metadatas"][i]

                documents.append(doc_data)

            total_count = collection.count()

            logger.info(
                f"Listed {len(documents)} documents from '{collection_name}' "
                f"(total: {total_count})"
            )

            return {
                "collection_name": collection_name,
                "total_documents": total_count,
                "offset": offset,
                "limit": limit,
                "returned_count": len(documents),
                "documents": documents,
            }

        except Exception as e:
            if isinstance(e, ChromaDBError):
                raise

            raise ChromaDBError(
                f"Failed to list documents in collection: {collection_name}",
                error_code=1442,
                context={"collection_name": collection_name},
                cause=e,
            )

    def delete_documents(
        self, collection_name: str, document_ids: List[str]
    ) -> Dict[str, Any]:
        """Delete specific documents from collection.

        Args:
            collection_name: Name of collection
            document_ids: List of document IDs to delete

        Returns:
            Dictionary with deletion results

        Raises:
            ChromaDBError: If deletion fails
        """
        if not self.client._connection_validated:
            raise ChromaDBError(
                "ChromaDB connection not established",
                error_code=1400,
                context={"operation": "delete_documents"},
            )

        try:
            collection = self.client.client.get_collection(collection_name)

            # Delete documents
            collection.delete(ids=document_ids)

            logger.info(
                f"Deleted {len(document_ids)} documents from "
                f"'{collection_name}'"
            )

            return {
                "collection_name": collection_name,
                "deleted_count": len(document_ids),
                "deleted_ids": document_ids,
            }

        except Exception as e:
            raise ChromaDBError(
                f"Failed to delete documents from collection: "
                f"{collection_name}",
                error_code=1443,
                context={
                    "collection_name": collection_name,
                    "document_ids": document_ids,
                },
                cause=e,
            )

    def _process_query_results(
        self,
        results: Dict,
        similarity_threshold: float,
        include_metadata: bool,
    ) -> Dict[str, Any]:
        """Process and filter query results.

        Args:
            results: Raw query results from ChromaDB
            similarity_threshold: Minimum similarity score
            include_metadata: Whether metadata is included

        Returns:
            Processed results dictionary
        """
        processed = {"results": []}

        if not results.get("ids") or not results["ids"][0]:
            return processed

        ids = results["ids"][0]
        documents = results["documents"][0]
        distances = results["distances"][0]
        metadatas = (
            results.get("metadatas", [[]])[0] if include_metadata else []
        )

        for i, doc_id in enumerate(ids):
            # Convert distance to similarity score (ChromaDB uses distance,
            # lower is better)
            similarity = max(0, 1 - distances[i])

            # Apply similarity threshold
            if similarity < similarity_threshold:
                continue

            result_item = {
                "id": doc_id,
                "content": documents[i],
                "similarity_score": round(similarity, 4),
                "distance": round(distances[i], 4),
            }

            if include_metadata and i < len(metadatas):
                result_item["metadata"] = metadatas[i]

            processed["results"].append(result_item)

        return processed

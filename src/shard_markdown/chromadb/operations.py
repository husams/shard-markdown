"""ChromaDB query and retrieval operations."""

from typing import Any, cast

from ..utils.errors import ChromaDBError
from ..utils.logging import get_logger
from .protocol import ChromaDBClientProtocol


logger = get_logger(__name__)


class ChromaDBOperations:
    """High-level ChromaDB operations for querying and retrieval."""

    def __init__(self, client: ChromaDBClientProtocol) -> None:
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
    ) -> dict[str, Any]:
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
        if not self.client._connection_validated or self.client.client is None:
            raise ChromaDBError(
                "ChromaDB connection not established",
                error_code=1400,
                context={"operation": "query_collection"},
            )

        try:
            collection = self.client.client.get_collection(collection_name)

            # Prepare include list - use Any for chromadb compatibility
            include: Any = [
                "documents",
                "distances",
            ]
            if include_metadata:
                include.append("metadatas")

            # Perform query
            results = collection.query(
                query_texts=[query_text],
                n_results=limit,
                include=include,
            )

            # Process results
            processed_results = self._process_query_results(
                cast(dict[str, Any], results), similarity_threshold, include_metadata
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

        except (ValueError, RuntimeError, KeyError, AttributeError) as e:
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
            ) from e

    def get_document(
        self,
        collection_name: str,
        document_id: str,
        include_metadata: bool = True,
    ) -> dict[str, Any] | None:
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
        if not self.client._connection_validated or self.client.client is None:
            raise ChromaDBError(
                "ChromaDB connection not established",
                error_code=1400,
                context={"operation": "get_document"},
            )

        try:
            collection = self.client.client.get_collection(collection_name)

            # Prepare include list - use Any for chromadb compatibility
            include: Any = ["documents"]
            if include_metadata:
                include.append("metadatas")

            # Get document
            results = collection.get(ids=[document_id], include=include)

            if not results["ids"]:
                return None

            # Format result
            document_data: dict[str, Any] = {
                "id": results["ids"][0],
                "content": results["documents"][0] if results["documents"] else "",
            }

            if include_metadata and results.get("metadatas"):
                metadatas = results.get("metadatas")
                if metadatas and isinstance(metadatas, list) and len(metadatas) > 0:
                    document_data["metadata"] = metadatas[0]

            logger.info(
                "Retrieved document '%s' from '%s'", document_id, collection_name
            )

            return document_data

        except (ValueError, RuntimeError, KeyError, AttributeError) as e:
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
            ) from e

    def list_documents(
        self,
        collection_name: str,
        limit: int = 100,
        offset: int = 0,
        include_metadata: bool = False,
    ) -> dict[str, Any]:
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
        if not self.client._connection_validated or self.client.client is None:
            raise ChromaDBError(
                "ChromaDB connection not established",
                error_code=1400,
                context={"operation": "list_documents"},
            )

        try:
            collection = self.client.client.get_collection(collection_name)

            # Prepare include list - use Any for chromadb compatibility
            include: Any = ["documents"]
            if include_metadata:
                include.append("metadatas")

            # Get documents
            results = collection.get(limit=limit, offset=offset, include=include)

            # Format results
            documents = []
            for i, doc_id in enumerate(results["ids"]):
                doc_data = {
                    "id": doc_id,
                    "content": (
                        results["documents"][i][:200] + "..."
                        if results["documents"]
                        and i < len(results["documents"])
                        and len(results["documents"][i]) > 200
                        else (
                            results["documents"][i]
                            if results["documents"] and i < len(results["documents"])
                            else ""
                        )
                    ),
                    "content_length": (
                        len(results["documents"][i])
                        if results["documents"] and i < len(results["documents"])
                        else 0
                    ),
                }

                if include_metadata:
                    metadatas = results.get("metadatas")
                    if metadatas and isinstance(metadatas, list) and i < len(metadatas):
                        doc_data["metadata"] = metadatas[i]

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

        except (ValueError, RuntimeError, KeyError, AttributeError) as e:
            if isinstance(e, ChromaDBError):
                raise

            raise ChromaDBError(
                f"Failed to list documents in collection: {collection_name}",
                error_code=1442,
                context={"collection_name": collection_name},
                cause=e,
            ) from e

    def delete_documents(
        self, collection_name: str, document_ids: list[str]
    ) -> dict[str, Any]:
        """Delete specific documents from collection.

        Args:
            collection_name: Name of collection
            document_ids: List of document IDs to delete

        Returns:
            Dictionary with deletion results

        Raises:
            ChromaDBError: If deletion fails
        """
        if not self.client._connection_validated or self.client.client is None:
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
                f"Deleted {len(document_ids)} documents from '{collection_name}'"
            )

            return {
                "collection_name": collection_name,
                "deleted_count": len(document_ids),
                "deleted_ids": document_ids,
            }

        except (ValueError, RuntimeError, KeyError, AttributeError) as e:
            raise ChromaDBError(
                f"Failed to delete documents from collection: {collection_name}",
                error_code=1443,
                context={
                    "collection_name": collection_name,
                    "document_ids": document_ids,
                },
                cause=e,
            ) from e

    def _process_query_results(
        self,
        results: dict[str, Any],
        similarity_threshold: float,
        include_metadata: bool,
    ) -> dict[str, Any]:
        """Process and filter query results.

        Args:
            results: Raw query results from ChromaDB
            similarity_threshold: Minimum similarity score
            include_metadata: Whether metadata is included

        Returns:
            Processed results dictionary
        """
        processed: dict[str, Any] = {"results": []}

        if not results.get("ids") or not results["ids"][0]:
            return processed

        ids = results["ids"][0]
        documents = results["documents"][0]
        distances = results["distances"][0]
        metadatas = results.get("metadatas", [[]])[0] if include_metadata else []

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

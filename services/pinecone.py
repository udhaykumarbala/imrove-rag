from pinecone.grpc import PineconeGRPC as Pinecone
from typing import List, Dict, Any, Optional
import os
from config import settings

class PineconeService:
    def __init__(self):
        """Initialize Pinecone connection."""
        self._load_env_variables()
        self._initialize_pinecone()

    def _load_env_variables(self) -> None:
        """Load environment variables."""
        self.api_key = settings.PINECONE_API_KEY
        self.index_name = settings.PINECONE_INDEX_NAME
        self.namespace = "Developement"
        if not all([self.api_key, self.index_name]):
            raise ValueError("Missing required environment variables")

    def _initialize_pinecone(self) -> None:
        """Initialize Pinecone with API key."""
        pc = Pinecone(api_key=self.api_key)
        indexes = [idx.name for idx in pc.list_indexes()]
        if self.index_name not in indexes:
            raise ValueError(f"Index '{self.index_name}' does not exist")
        self.index = pc.Index(self.index_name)

    def upsert_vectors(self, vectors: List[Dict[str, Any]]) -> bool:
        """
        Upsert vectors to Pinecone index.
        Args:
            vectors: List of dictionaries containing 'id', 'values', and optional 'metadata'
        Returns:
            bool: Success status
        """
        try:
            self.index.upsert(vectors=vectors, namespace=self.namespace)
            return True
        except Exception as e:
            print(f"Error upserting vectors: {e}")
            return False

    def delete_vectors(self, ids: List[str]) -> bool:
        """
        Delete vectors from Pinecone index.
        Args:
            ids: List of vector IDs to delete
        Returns:
            bool: Success status
        """
        try:
            self.index.delete(ids=ids, namespace=self.namespace)
            return True
        except Exception as e:
            print(f"Error deleting vectors: {e}")
            return False

    def fetch_vectors(self, ids: List[str]) -> Optional[Dict]:
        """
        Fetch vectors from Pinecone index.
        Args:
            ids: List of vector IDs to fetch
        Returns:
            Optional[Dict]: Fetched vectors or None if error occurs
        """
        try:
            return self.index.fetch(ids=ids, namespace=self.namespace)
        except Exception as e:
            print(f"Error fetching vectors: {e}")
            return None

    def query_vectors(self, vector: List[float], top_k: int = 3, include_metadata: bool = True) -> Optional[Dict]:
        """
        Query similar vectors from Pinecone index.
        Args:
            vector: Query vector
            top_k: Number of similar vectors to return
            include_metadata: Whether to include metadata in results
        Returns:
            Optional[Dict]: Query results or None if error occurs
        """
        try:
            return self.index.query(
                vector=vector,
                top_k=top_k,
                include_metadata=include_metadata,
                namespace=self.namespace
            )
        except Exception as e:
            print(f"Error querying vectors: {e}")
            return None
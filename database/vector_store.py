import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any

class VectorStore:
    def __init__(self):
        self.client = chromadb.PersistentClient()  # Replace the old Settings()-based initialization
        self.collection = self.client.get_or_create_collection("loan_documents")
    
    def store_document(self, document_info: Dict[str, Any], document_id: str):
        if not document_id:
            raise ValueError("document_id cannot be None or empty")
            
        print("document is pushed to vector store")
        text_content = str(document_info)
        self.collection.add(
            documents=[text_content],
            metadatas=[document_info],
            ids=[document_id]
        )
    
    def search_documents(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        return results['metadatas'][0]
    
    def check_if_document_exists(self, document_id: str) -> bool:
        if not document_id:
            return False
            
        try:
            result = self.index.fetch(ids=[document_id])
            return len(result.vectors) > 0
        except Exception:
            return False
    
    def update_document(self, document_info: Dict[str, Any], document_id: str):
        if not document_id:
            raise ValueError("document_id cannot be None or empty")
        self.collection.remove(document_id)
        self.store_document(document_info, document_id)
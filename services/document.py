from typing import List, Optional
from databases.mongo import MongoDB
from models.document import LoanDocument

class DocumentService:
    def __init__(self):
        self.client = MongoDB().connect()
        self.loan_documents = self.client.get_collection('loan_documents')
        
        # Create text index on relevant fields
        self.loan_documents.create_index([
            ("lender_name", "text"),
            ("loan_type", "text"),
            ("loan_purpose", "text"),
            ("property_type", "text"),
            ("loan_terms", "text")
        ])

    def store_document(self, document: LoanDocument) -> LoanDocument:
        loan_document = document.to_dict()
        self.loan_documents.insert_one(loan_document)
        return document

    def get_document_by_id(self, document_id: str) -> Optional[LoanDocument]:
        data = self.loan_documents.find_one({"document_id": document_id})
        return LoanDocument.from_dict(data) if data else None

    def update_document(self, document_id: str, updates: dict) -> bool:
        if "document_id" in updates:
            del updates["document_id"]  # Ensure document_id is not overwritten
        result = self.loan_documents.update_one(
            {"document_id": document_id},
            {"$set": updates}
        )
        return result.modified_count > 0

    def delete_document(self, document_id: str) -> bool:
        result = self.loan_documents.delete_one({"document_id": document_id})
        return result.deleted_count > 0
        
    def search_documents(self, query: dict) -> list[LoanDocument]:
        documents = self.loan_documents.find(query)
        return [doc for doc in list(documents)]

    def find_similar_documents(self, document: LoanDocument) -> List[LoanDocument]:
        query = {"company_name": document.company_name}
        documents = self.loan_documents.find(query)
        return [doc for doc in list(documents)]
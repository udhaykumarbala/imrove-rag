from datetime import datetime
from typing import Optional
from pymongo import MongoClient
from bson import ObjectId
from config import settings

## Document create, delete
## Updating existing document based on document id
## Search Document based on query parameter


class Document:
    def __init__(self, email: str, name: Optional[str] = None, user_id: Optional[str] = None, created: Optional[datetime] = None):
        self.id = user_id or str(ObjectId()) ## required
        self.email = email
        self.name = name
        self.created = created or datetime.utcnow() ## required

    def to_dict(self):
        data = {
            "_id": ObjectId(self.id),
            "email": self.email,
            "created": self.created
        }
        if self.name:
            data["name"] = self.name
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        return cls(
            email=data["email"],
            name=data.get("name"),
            user_id=str(data["_id"]),
            created=data["created"]
        )

class DocumentStore:
    def __init__(self):
        self.client = MongoClient(settings.MONGODB_URL)
        self.db = self.client[settings.MONGO_DATABASE]
        self.users = self.db.users

    def create_user(self, email: str) -> User:
        # Check if user already exists
        if self.get_user_by_email(email):
            raise ValueError("User with this email already exists")
        
        user = User(email=email)
        self.users.insert_one(user.to_dict())
        return user

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        user_data = self.users.find_one({"_id": ObjectId(user_id)})
        return User.from_dict(user_data) if user_data else None

    def get_user_by_email(self, email: str) -> Optional[User]:
        user_data = self.users.find_one({"email": email})
        return User.from_dict(user_data) if user_data else None

    def update_user(self, user: User) -> bool:
        result = self.users.update_one(
            {"_id": ObjectId(user.id)},
            {"$set": {"name": user.name, "email": user.email}}
        )
        return result.modified_count > 0

    def delete_user(self, user_id: str) -> bool:
        result = self.users.delete_one({"_id": ObjectId(user_id)})
        return result.deleted_count > 0

    def update_user_name(self, user_id: str, name: str) -> bool:
        if not name or not name.strip():
            raise ValueError("Name cannot be empty")

        result = self.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"name": name.strip()}}
        )
        return result.modified_count > 0

    def is_user_profile_complete(self, user_id: str) -> bool:
        user_data = self.users.find_one({"_id": ObjectId(user_id)})
        if not user_data:
            return False
        return bool(user_data.get("name"))



from datetime import datetime
from typing import Optional
from pymongo import MongoClient
from bson import ObjectId
from pydantic import BaseModel, Field

# Replace with your actual MongoDB settings
MONGODB_URL = "your_mongodb_url"
MONGO_DATABASE = "your_database_name"

class ContactInformation(BaseModel):
    name: str = Field(description="Contact person's name", default="MISSING")
    phone: str = Field(description="Contact phone number", default="MISSING")
    address: str = Field(description="Contact address", default="MISSING")
    email: str = Field(description="Contact email address", default="MISSING")

class LoanDocument(BaseModel):
    id: Optional[str] = Field(default_factory=lambda: str(ObjectId()), description="Unique document ID")
    company_name: str = Field(description="Name of the company providing the loan services.", default="MISSING")
    loan_plans: str = Field(description="Details of the loan plans offered.", default="MISSING")
    service_area: str = Field(description="Geographical regions where the company provides its loan services.", default="MISSING")
    credit_score_requirements: str = Field(description="Minimum credit score required to qualify for the loan.", default="MISSING")
    loan_minimum_amount: str = Field(description="The minimum loan amount that can be availed.", default="MISSING")
    loan_maximum_amount: str = Field(description="The maximum loan amount that can be availed.", default="MISSING")
    loan_to_value_ratio: str = Field(description="Loan-to-Value (LTV) ratio, typically expressed as a percentage.", default="MISSING")
    application_requirements: str = Field(description="List of documents or criteria required to apply for the loan.", default="MISSING")
    guidelines: str = Field(description="Guidelines and instructions related to the loan application process.", default="MISSING")
    contact_information: ContactInformation = Field(description="Details for contacting the company, including name, phone, address, and email.")
    property_types: str = Field(description="Types of properties eligible for loans, such as residential, commercial, etc.", default="MISSING")
    interest_rates: str = Field(description="Details about the interest rates applicable to the loan.", default="MISSING")
    points_charged: str = Field(description="Points or fees charged on the loan, often expressed as a percentage of the loan amount.", default="MISSING")
    liquidity_requirements: str = Field(description="Minimum liquidity required by the borrower to qualify for the loan.", default="MISSING")
    loan_to_cost_ratio: str = Field(description="Loan-to-Cost (LTC) ratio, typically expressed as a percentage.", default="MISSING")
    debt_service_coverage_ratio: str = Field(description="Debt Service Coverage Ratio (DSCR), representing the minimum income to cover debt obligations.", default="MISSING")
    loan_term: str = Field(description="Duration of the loan, usually expressed in months or years.", default="MISSING")
    amortization: str = Field(description="Details of the amortization schedule, specifying how the loan will be repaid.", default="MISSING")
    construction: str = Field(description="Indicates whether the loan is applicable for construction projects (yes/no).", default="MISSING")
    value_add: str = Field(description="Indicates whether the loan is applicable for value-add projects (yes/no).", default="MISSING")
    personal_guarantee: str = Field(description="Specifies if a personal guarantee is required for the loan (yes/no/partial).", default="MISSING")
    created: datetime = Field(default_factory=datetime.utcnow, description="Document creation timestamp.")

    def to_dict(self):
        return self.dict(by_alias=True, exclude_none=True, exclude_unset=True)

class LoanDocumentStore:
    def __init__(self):
        self.client = MongoClient(MONGODB_URL)
        self.db = self.client[MONGO_DATABASE]
        self.collection = self.db.loan_documents

    def create_document(self, document: LoanDocument) -> LoanDocument:
        self.collection.insert_one(document.to_dict())
        return document

    def get_document_by_id(self, document_id: str) -> Optional[LoanDocument]:
        data = self.collection.find_one({"_id": ObjectId(document_id)})
        return LoanDocument(**data) if data else None

    def update_document(self, document_id: str, updates: dict) -> bool:
        result = self.collection.update_one(
            {"_id": ObjectId(document_id)},
            {"$set": updates}
        )
        return result.modified_count > 0

    def delete_document(self, document_id: str) -> bool:
        result = self.collection.delete_one({"_id": ObjectId(document_id)})
        return result.deleted_count > 0

    def search_documents(self, query: dict) -> list[LoanDocument]:
        documents = self.collection.find(query)
        return [LoanDocument(**doc) for doc in documents]

# Example Usage:
# store = LoanDocumentStore()
# new_doc = LoanDocument(company_name="ABC Loans", contact_information=ContactInformation(name="John Doe", phone="1234567890", address="123 Main St", email="john@abc.com"))
# store.create_document(new_doc)

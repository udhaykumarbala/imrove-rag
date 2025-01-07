from datetime import datetime
from typing import Optional, List
from pymongo import MongoClient
from bson import ObjectId
from config import settings

class LoanDocument:
    def __init__(
        self,
        document_id: str = "MISSING",
        company_name: str = "MISSING",
        loan_plans: str = "MISSING",
        service_areas: str = "MISSING",
        credit_score_requirements: str = "MISSING",
        loan_amount: dict = {"min": "MISSING", "max": "MISSING"},
        ltv_ratio: dict = {"min": "MISSING", "max": "MISSING"},
        application_requirements: List[str] = ["MISSING"],
        guidelines: List[str] = ["MISSING"],
        contact_information: Optional[dict] = {"person": "MISSING", "phone": "MISSING", "email": "MISSING"},
        property_types: List[str] = ["MISSING"],
        interest_rate: dict = {"min": "MISSING", "max": "MISSING"},
        points_charged: dict = {"min": "MISSING", "max": "MISSING"},
        liquidity_requirements: List[str] = ["MISSING"],
        ltc_ratio: dict = {"min": "MISSING", "max": "MISSING"},
        dscr: dict = {"min": "MISSING", "max": "MISSING"},
        loan_term: dict = {"min": "MISSING", "max": "MISSING"},
        amortization: str = "MISSING",
        construction: str = "MISSING",
        value_add: str = "MISSING",
        personal_guarantee: str = "MISSING",
        created_at: datetime = datetime.utcnow(),
        updated_at: datetime = datetime.utcnow(),
        created_by: str = "MISSING"
    ):
        self.id = str(ObjectId())
        self.document_id = document_id
        self.company_name = company_name
        self.loan_plans = loan_plans
        self.service_areas = service_areas
        self.credit_score_requirements = credit_score_requirements
        self.loan_amount = loan_amount
        self.ltv_ratio = ltv_ratio
        self.application_requirements = application_requirements
        self.guidelines = guidelines
        self.contact_information = contact_information or {"person": "MISSING", "phone": "MISSING", "email": "MISSING"}
        self.property_types = property_types
        self.interest_rate = interest_rate
        self.points_charged = points_charged
        self.liquidity_requirements = liquidity_requirements
        self.ltc_ratio = ltc_ratio
        self.dscr = dscr
        self.loan_term = loan_term
        self.amortization = amortization
        self.construction = construction
        self.value_add = value_add
        self.personal_guarantee = personal_guarantee
        self.created_at = created_at
        self.updated_at = updated_at
        self.created_by = created_by

    def to_dict(self):
        return {
            "_id": ObjectId(self.id),
            "document_id": self.document_id,
            "company_name": self.company_name,
            "loan_plans": self.loan_plans,
            "service_areas": self.service_areas,
            "credit_score_requirements": self.credit_score_requirements,
            "loan_amount": self.loan_amount,
            "ltv_ratio": self.ltv_ratio,
            "application_requirements": self.application_requirements,
            "guidelines": self.guidelines,
            "contact_information": self.contact_information,
            "property_types": self.property_types,
            "interest_rate": self.interest_rate,
            "points_charged": self.points_charged,
            "liquidity_requirements": self.liquidity_requirements,
            "ltc_ratio": self.ltc_ratio,
            "dscr": self.dscr,
            "loan_term": self.loan_term,
            "amortization": self.amortization,
            "construction": self.construction,
            "value_add": self.value_add,
            "personal_guarantee": self.personal_guarantee,
            "created_at": self.created_at.timestamp(),
            "updated_at": self.updated_at.timestamp(),
            "created_by": self.created_by,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LoanDocument":
        return cls(
            document_id=data.get("document_id", "MISSING"),
            company_name=data.get("company_name", "MISSING"),
            loan_plans=data.get("loan_plans", "MISSING"),
            service_areas=data.get("service_areas", "MISSING"),
            credit_score_requirements=data.get("credit_score_requirements", "MISSING"),
            loan_amount=data.get("loan_amount", {"min": "MISSING", "max": "MISSING"}),
            ltv_ratio=data.get("ltv_ratio", {"min": "MISSING", "max": "MISSING"}),
            application_requirements=data.get("application_requirements", ["MISSING"]),
            guidelines=data.get("guidelines", ["MISSING"]),
            contact_information=data.get("contact_information", {"person": "MISSING", "phone": "MISSING", "email": "MISSING"}),
            property_types=data.get("property_types", ["MISSING"]),
            interest_rate=data.get("interest_rate", {"min": "MISSING", "max": "MISSING"}),
            points_charged=data.get("points_charged", {"min": "MISSING", "max": "MISSING"}),
            liquidity_requirements=data.get("liquidity_requirements", ["MISSING"]),
            ltc_ratio=data.get("ltc_ratio", {"min": "MISSING", "max": "MISSING"}),
            dscr=data.get("dscr", {"min": "MISSING", "max": "MISSING"}),
            loan_term=data.get("loan_term", {"min": "MISSING", "max": "MISSING"}),
            amortization=data.get("amortization", "MISSING"),
            construction=data.get("construction", "MISSING"),
            value_add=data.get("value_add", "MISSING"),
            personal_guarantee=data.get("personal_guarantee", "MISSING"),
            created_at=datetime.fromtimestamp(data["created_at"]),
            updated_at=datetime.fromtimestamp(data["updated_at"]),
            created_by=data.get("created_by", "MISSING"),
        )

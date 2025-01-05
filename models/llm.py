from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr, conlist
from datetime import datetime
from enum import Enum


class ContactInfo(BaseModel):
    person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None

class RangeValue(BaseModel):
    min: Any = None
    max: Any = None

class AnalyzeIntent(BaseModel):
    intent: str = Field(description="Identified intent of the user's message.")
    confidence: str = Field(description="Confidence of the indentified intent based on user message (High/Medium/Low)")
    reason: str = Field(description="Brief explanation for the classification based on the user message and conversation history.")

class LoanDocument(BaseModel):
    company_name: str = Field(description="Name of the loan company")
    loan_plans: str = Field(description="List of loan plans offered by the company")
    service_areas: List[str] = Field(description="List of state codes where the company operates")
    credit_score_requirements: Optional[RangeValue] = Field(description="Credit score range required for loan approval", default=RangeValue(min="Missing", max="Missing"))
    loan_amount: RangeValue = Field(description="Range of loan amounts offered by the company", default=RangeValue(min="Missing", max="Missing"))
    ltv_ratio: RangeValue = Field(description="Loan-to-value ratio range", default=RangeValue(min="Missing", max="Missing"))
    application_requirements: List[str] = Field(description="List of documents and criteria required for loan application")
    guidelines: List[str] = Field(default_factory=list, description="List of guidelines for loan approval")
    contact_information: ContactInfo = Field(description="Contact information of the loan company")
    property_types: List[str] = Field(description="Types of properties eligible for loans")
    interest_rate: RangeValue = Field(description="Interest rate charged on the loan", default=RangeValue(min="Missing", max="Missing"))
    points_charged: RangeValue = Field(description="Range of points charged on the loan", default=RangeValue(min="Missing", max="Missing"))
    liquidity_requirements: List[str] = Field(default_factory=list, description="Liquidity requirements for loan approval")
    ltc_ratio: RangeValue = Field(description="Loan-to-cost ratio range", default=RangeValue(min="Missing", max="Missing"))
    dscr: RangeValue = Field(description="Range of debt service coverage ratio required", default=RangeValue(min="Missing", max="Missing"))
    loan_term: RangeValue = Field(description="Range of loan terms offered by the company in years", default=RangeValue(min="Missing", max="Missing"))
    amortization: str = Field(description="Amortization period in years")
    construction: str = Field(description="Whether the loan is for construction purposes", default="Missing")
    value_add: str = Field(description="Whether the loan is for value-add purposes", default="Missing")
    personal_guarantee: str = Field(description="Whether a personal guarantee is required", default="Missing")

class UploadDocument(BaseModel):
    extracted_info: LoanDocument = Field(description="Data extracted from Loan document")
    message: str = Field(description="Generated User message")
    chat_title: str = Field(description="A short title less than 4 words for the document")

class UploadChat(BaseModel):
    extracted_info: LoanDocument = Field(description="Data extracted from Loan document")
    message: str = Field(description="Generated User message")
    consent: bool = Field(default=False)
    is_updated: bool = Field(default=False)
    chat_title: str = Field(description="A short title less than 4 words for the document")

class CheckRelevance(BaseModel):
    document_type: str = Field(description="Identified type of the document based on the content.")
    confidence: str = Field(description="Confidence of the indentified type based on the content (High/Medium/Low)")

class Filters(BaseModel):
    field: str = Field(description="Field to filter (e.g., name, service_area) mentioned in user message")
    operator: str = Field(description="Operator (e.g., '=', 'contains', 'startswith', 'textsearch').")
    value: Any = Field(description="Value or pattern for the filter.")

class FeaturesFromChat(BaseModel):
    filters: List[Filters] = Field(description="List of all responsible filters extracted from user's message")

class Response(BaseModel):
    response: str = Field(description="The response generated for the user based on their input, providing relevant information or assistance.")
    chat_title: str = Field(description="A short title less than 4 words for the conversation")
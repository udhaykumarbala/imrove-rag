from .base import BaseLLM
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from openai import OpenAI
import json
import logging
import base64

from langchain_openai import ChatOpenAI
from langchain_core.utils.function_calling import convert_to_openai_function
from langchain_core.prompts import ChatPromptTemplate

from utils.prompt import *

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IntentResponse(BaseModel):
    intent: str = Field(description="Identified intent of the user's message.")
    confidence: str = Field(description="Confidence of the indentified intent based on user message (High/Medium/Low)")
    reason: str = Field(description="Brief explanation for the classification based on the user message and conversation history.")

class CheckRelevanceResponse(BaseModel):
    document_type: str = Field(description="Identified type of the document based on the content.")
    confidence: str = Field(description="Confidence of the indentified type based on the content (High/Medium/Low)")

class ChatResponse(BaseModel):
    response: str = Field(description="The response generated for the user based on their input, providing relevant information or assistance.")
    chat_title: str = Field(description="A short title less than 4 words for the conversation")
    
class ContactInformation(BaseModel):
    person: str = Field(description="Contact person's name.", default="MISSING")
    address: str = Field(description="Company's physical address.", default="MISSING")
    phone_number: str = Field(description="Contact phone number.", default="MISSING")
    website: str = Field(description="Company's official website.", default="MISSING")
    email: str = Field(description="Contact email address.", default="MISSING")

class MinMaxValues(BaseModel):
    min: Any = Field(description="Minimum value, can be a string or a float.", default=0)
    max: Any = Field(description="Maximum value, can be a string or a float.", default=0)
    
class DataFromDoc(BaseModel):
    company_name: str = Field(description="Company name providing the loan services.", default="MISSING")
    loan_plans: str = Field(description="Details of the loan plans offered.", default="MISSING")
    service_area: List[str] = Field(description="Regions where the company provides loan services.", default=["MISSING"])
    credit_score_requirements: str = Field(description="Minimum credit score required.", default="MISSING")
    loan_minimum_amount: float = Field(description="Minimum loan amount (float).", default=0)
    loan_maximum_amount: float = Field(description="Maximum loan amount (float).", default=0)
    loan_to_value_ratio: MinMaxValues = Field(description="Loan-to-Value (LTV) ratio (float).", default=0)
    application_requirements: str = Field(description="Documents or criteria required to apply.", default="MISSING")
    guidelines: str = Field(description="Guidelines for the loan application process.", default="MISSING")
    contact_information: ContactInformation = Field(description="Contact details including name, phone, address, and email.", default="MISSING")
    property_types: str = Field(description="Eligible property types (e.g., residential, commercial).", default="MISSING")
    interest_rates: MinMaxValues = Field(description="Interest rates applicable to the loan.", default="MISSING")
    points_charged: MinMaxValues = Field(description="Points or fees charged on the loan.", default="MISSING")
    liquidity_requirements: str = Field(description="Minimum liquidity required by the borrower.", default="MISSING")
    loan_to_cost_ratio: MinMaxValues = Field(description="Loan-to-Cost (LTC) ratio (float).", default=0)
    debt_service_coverage_ratio: MinMaxValues = Field(description="Debt Service Coverage Ratio (DSCR) (float).", default=0)
    loan_term: MinMaxValues = Field(description="Loan duration (months or years).", default="MISSING")
    amortization: str = Field(description="Amortization schedule details.", default="MISSING")
    construction: str = Field(description="Applicable for construction projects (yes/no).", default="MISSING")
    value_add: str = Field(description="Applicable for value-add projects (yes/no).", default="MISSING")
    personal_guarantee: str = Field(description="Personal guarantee requirement (yes/no/partial).", default="MISSING")

class ExtractDocInfoResponse(BaseModel):
    extracted_info: DataFromDoc = Field(description="Data extracted from Loan document")
    message: str = Field(description="Generated User message")
    consent: bool = Field(default=False)
    is_updated: bool = Field(default=False)
    chat_title: str = Field(description="A short title less than 4 words for the document")

class FilterInformation(BaseModel):
    field: str = Field(description="Field to filter (e.g., name, service_area) mentioned in user message")
    operator: str = Field(description="Operator (e.g., '=', 'contains', 'startswith', 'textsearch').")
    value: Any = Field(description="Value or pattern for the filter.")

class ExtractFeatureResponse(BaseModel):
    filters: List[FilterInformation] = Field(description="List of all responsible filters extracted from user's message")

class XAIHandler(BaseLLM):
    def __init__(self, api_key: str):
        self.client = ChatOpenAI(
            model="grok-beta", 
            temperature=0, 
            timeout=None, 
            max_retries=3, 
            max_tokens=None, 
            base_url="https://api.x.ai/v1", 
            api_key=api_key,
            )
        self.logger = logging.getLogger(__name__)

    async def generate_response(self, intent, message, conversation, kb_result_str):
        try:
            conversation_payload = [("system", general_leading_prompt)]

            if conversation:
                conversation_payload.extend([(msg["role"], msg["content"]) for msg in conversation])
            
            conversation_payload.append(("user", message))

            prompt = ChatPromptTemplate.from_messages(conversation_payload)
            response = { "response": "" }

            if intent == 'filtered_lender' or intent == 'follow_up_lender':
                conversation_payload = [("system", filtered_lender_prompt)]
                if conversation:
                    conversation_payload.extend([(msg["role"], msg["content"]) for msg in conversation])
                conversation_payload.append(("user", message))
                prompt = ChatPromptTemplate.from_messages(conversation_payload)
                chain = prompt | self.client.with_structured_output(ChatResponse)
                print('kb_result_str', kb_result_str)
                response = chain.invoke({"relevant_lenders": kb_result_str})

            elif intent == "criteria_missing":
                conversation_payload = [("system", criteria_missing_prompt)]
                if conversation:
                    conversation_payload.extend([(msg["role"], msg["content"]) for msg in conversation])
                conversation_payload.append(("user", message))
                prompt = ChatPromptTemplate.from_messages(conversation_payload)
                chain = prompt | self.client.with_structured_output(ChatResponse)
                response = chain.invoke({"messages": conversation_payload})

            else: 
                chain = prompt | self.client.with_structured_output(ChatResponse)
                response = chain.invoke({"messages": conversation_payload})

            return response

        except Exception as e:
            print(f"Error generating response: {e}")
            return type('Response', (object,), {
                "response": "I'm sorry, I couldn't generate a response. Please try again.",
                "chat_title": ""
            })()
    
    async def analyze_intent(self, message: str, conversation: list):
        try:
            recent_messages = conversation[-10:] if conversation else []

            conversation_payload = [("system", intent_anlyse_prompt)]

            if recent_messages:
                conversation_payload.extend([(msg["role"], msg["content"]) for msg in recent_messages])

            conversation_payload.append(("user", message))

            prompt = ChatPromptTemplate.from_messages(conversation_payload)
            chain = prompt | self.client.with_structured_output(IntentResponse)
            response = chain.invoke({"messages": conversation_payload})
                    
            return response

        except Exception as e:
            self.logger.error(f"Error analyzing intent: {e}")
            return "other"

    # upload
    def extract_document_info(self, text: str, user_id: str = None) -> Dict[str, str]:
        try:
            prompt = ChatPromptTemplate.from_messages([("system", extract_document_info_prompt)])
            chain = prompt | self.client.with_structured_output(ExtractDocInfoResponse)
            response = chain.invoke({"document_content": text})
            
            if user_id and response.extracted_info:
                response.extracted_info.created_by = user_id
                
            return response

        except Exception as e:
            self.logger.error(f"Error extracting information from document: {e}")
            return {}
    
    # upload chat 
    def extract_document_info_from_conversation(
        self, 
        prompt: str, 
        conversation: List[Dict[str, str]], 
        previous_info: Dict[str, str],
        user_id: str = None
    ) -> Dict[str, str]:
        try:
            conversation_payload = [("system", extract_info_from_conversation_prompt)]

            if conversation:
                conversation_payload.extend([(msg["role"], msg["content"]) for msg in conversation])

            conversation_payload.append(("user", prompt))

            prompt = ChatPromptTemplate.from_messages(conversation_payload)
            chain = prompt | self.client.with_structured_output(ExtractDocInfoResponse)
            response = chain.invoke({"extracted_info": previous_info})
            
            if user_id and response.extracted_info:
                response.extracted_info.created_by = user_id
                
            return response

        except Exception as e:
            self.logger.error(f"Error extracting information from conversation: {e}")
            return previous_info

    # kv chat 
    def extract_feature_from_conversation(self,  message: str, conversation: list):
        try:

            recent_messages = conversation[-10:] if conversation else []
            conversation_payload = [("system", extract_feature_from_conversation_prompt)]

            if recent_messages:
                conversation_payload.extend([(msg["role"], msg["content"]) for msg in recent_messages])

            conversation_payload.append(("user", message))

            prompt = ChatPromptTemplate.from_messages(conversation_payload)
            chain = prompt | self.client.with_structured_output(ExtractFeatureResponse)
            response = chain.invoke({"messages": conversation_payload})
            response = response.model_dump()

            query = self._construct_mongo_query(response['filters'])
            return query

        except Exception as e:
            self.logger.error(f"Error extracting features from conversation: {e}")
            return "other"

    def check_relevance(self, text: str):
        try:
            prompt = ChatPromptTemplate.from_messages([("system", check_relevance_prompt)])
            chain = prompt | self.client.with_structured_output(CheckRelevanceResponse)
            response = chain.invoke({"document_content": text})
            return response.model_dump()

        except Exception as e:
            self.logger.error(f"Error extracting information from document: {e}")
            return {}

    def _construct_mongo_query(self, filters):
        regular_conditions = {}
        text_search = None

        print('filters', filters)

        for condition in filters:
            field = condition["field"]
            operator = condition["operator"]
            value = condition["value"]
            
            if field == "service_area":
                # Handle service_area specially as it's a list of state codes
                if operator in ["=", "contains"]:
                    regular_conditions[field] = value.upper()  # Exact match for state code
                elif operator == "textsearch":
                    # If searching multiple states at once
                    states = [s.strip().upper() for s in value.split(",")]
                    regular_conditions[field] = {"$in": states}
                continue

            if operator == "textsearch":
                # Modify text search to search for fields containing any of the words in value
                words = value.split()
                regex_pattern = "|".join(words)
                regular_conditions[field] = {"$regex": regex_pattern, "$options": "i"}
            elif operator == "=":
                regular_conditions[field] = value
            elif operator == "contains":
                regular_conditions[field] = {"$regex": value, "$options": "i"}
            elif operator == "startswith":
                regular_conditions[field] = {"$regex": f"^{value}", "$options": "i"}
            elif operator == ">":
                regular_conditions[field] = {"$gt": float(value)}
            elif operator == "<":
                regular_conditions[field] = {"$lt": float(value)}
            elif operator == ">=":
                regular_conditions[field] = {"$gte": float(value)}
            elif operator == "<=":
                regular_conditions[field] = {"$lte": float(value)}
            elif operator == "between":
                min_val, max_val = map(float, value.split(","))
                regular_conditions[field] = {"$gte": min_val, "$lte": max_val}
            elif operator == "range":
                min_value, max_value = value
                if min_value is not None:
                    regular_conditions[f"{field}.min"] = {"$gte": min_value}
                if max_value is not None:
                    regular_conditions[f"{field}.max"] = {"$lte": max_value}

        return regular_conditions


class XAIVisionHandler:
    def __init__(self, api_key: str):
        self.client = OpenAI(
            base_url="https://api.x.ai/v1", 
            api_key=api_key,
        )
        self.logger = logging.getLogger(__name__)

    def ocr(self, image_path: str) -> str:
        base64_image = self._encode_image(image_path)
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                            "detail": "high",
                        },
                    },
                    {
                        "type": "text",
                        "text": image_ocr_prompt,
                    },
                ],
            },
        ]
        ocr_content = self.client.chat.completions.create(
            model="grok-2-vision-1212",
            messages=messages,
            temperature=0.01,
        )
        return ocr_content.choices[0].message.content

    def _encode_image(self, image_path: str) -> str:
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
        return encoded_string
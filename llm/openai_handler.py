from .base import BaseLLM
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from openai import OpenAI
import json
import logging

from langchain_openai import ChatOpenAI
from langchain_core.utils.function_calling import convert_to_openai_function
from langchain_core.prompts import ChatPromptTemplate

from utils.prompt import intent_anlyse_prompt, extract_document_info_prompt, extract_info_from_conversation_prompt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IntentResponse(BaseModel):
    intent: str = Field(description="Identified intent of the user's message. Possible values include:\
- 'search': The user is asking about specific lenders or providing loan requirements.\
- 'more_info': The user is asking follow-up questions regarding previously discussed lenders or topics.\
- 'need_requirements': The user is looking for lender recommendations but has not provided enough information or requirements.\
- 'general_lending': The user is asking general questions about lending processes, terms, or concepts.\
- 'others': The message is unrelated to lending or loans.")

class ContactInformation(BaseModel):
    person: str = Field(description="Name of the contact person for the loan-related queries.")
    address: str = Field(description="Physical address of the company or branch offering the loan services.")
    phone_number: str = Field(description="Contact phone number for loan inquiries.")
    website: str = Field(description="Official website of the company providing the loan.")
    email: str = Field(description="Email address for correspondence regarding loan services.")

class DataFromDoc(BaseModel):
    company_name: str = Field(description="Name of the company providing the loan services.")
    loan_plans: str = Field(description="Details of the loan plans offered.")
    service_area: str = Field(description="Geographical regions where the company provides its loan services.")
    credit_score_requirements: str = Field(description="Minimum credit score required to qualify for the loan.")
    loan_minimum_amount: str = Field(description="The minimum loan amount that can be availed.")
    loan_maximum_amount: str = Field(description="The maximum loan amount that can be availed.")
    loan_to_value_ratio: str = Field(description="Loan-to-Value (LTV) ratio, typically expressed as a percentage.")
    application_requirements: str = Field(description="List of documents or criteria required to apply for the loan.")
    guidelines: str = Field(description="Guidelines and instructions related to the loan application process.")
    contact_information: ContactInformation = Field(description="Details for contacting the company, including name, phone, address and email.")
    property_types: str = Field(description="Types of properties eligible for loans, such as residential, commercial, etc.")
    interest_rates: str = Field(description="Details about the interest rates applicable to the loan.")
    points_charged: str = Field(description="Points or fees charged on the loan, often expressed as a percentage of the loan amount.")
    liquidity_requirements: str = Field(description="Minimum liquidity required by the borrower to qualify for the loan.")
    loan_to_cost_ratio: str = Field(description="Loan-to-Cost (LTC) ratio, typically expressed as a percentage.")
    debt_service_coverage_ration: str = Field(description="Debt Service Coverage Ratio (DSCR), representing the minimum income to cover debt obligations.")
    loan_term: str = Field(description="Duration of the loan, usually expressed in months or years.")
    amortization: str = Field(description="Details of the amortization schedule, specifying how the loan will be repaid.")
    construction: str = Field(description="Indicates whether the loan is applicable for construction projects (yes/no).")
    value_add: str = Field(description="Indicates whether the loan is applicable for value-add projects (yes/no).")
    personal_guarantee: str = Field(description="Specifies if a personal guarantee is required for the loan (yes/no/partial).")

class ExtractDocInfoResponse(BaseModel):
    extracted_info: DataFromDoc = Field(description="Data extracted from Loan document")
    message: str = Field(description="Generated User message")
    consent: bool = Field(default=False)
    is_updated: bool = Field(default=False)

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

    async def generate_response(self, prompt: str, context: List[Dict[str, str]]) -> str:
        messages = []
        
        # Add context messages first
        messages.extend(context)
        
        # Add the current prompt
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        try:
            response = self.client.chat.completions.create(
                model="grok-beta",
                messages=messages,
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise
    
    async def analyze_intent(self, message: str, conversation: list) -> str:
        
        try:
            recent_messages = conversation[-4:] if conversation else []

            prompt = ChatPromptTemplate.from_messages([("system", intent_anlyse_prompt)])
            chain = prompt | self.client.with_structured_output(IntentResponse)
            response = chain.invoke({"conversation_history": recent_messages, "user_message": message})

            cleaned_output = response.content.strip("```json\n").strip("\n```")
            parsed_output = json.loads(cleaned_output)
            
            #Extract just the intent category
            for intent_type in ['search', 'more_info', 'need_requirements', 'general_lending', 'others']:
                if intent_type in parsed_output["intent"]:
                    return intent_type
                    
            return 'others'

        except Exception as e:
            self.logger.error(f"Error analyzing intent: {e}")
            return 'others'

    def extract_document_info(self, text: str) -> Dict[str, str]:
        
        prompt = ChatPromptTemplate.from_messages([("system", extract_document_info_prompt)])
        chain = prompt | self.client.with_structured_output(ExtractDocInfoResponse)
        response = chain.invoke({"document_content": text})

        return response
    
    def extract_document_info_from_conversation(self, prompt: str, conversation: List[Dict[str, str]], previous_info: Dict[str, str]) -> Dict[str, str]:
        # Format previous info as a readable string
        previous_info_str = json.dumps(previous_info, indent=2)
        conversation_str = ""

        # Add conversation history
        if conversation:
            conversation_str = "\n".join(f"{msg['role']}: {str(msg['content'])}" for msg in conversation)
        
        conversation_str += "\n user: " + str(prompt)

        prompt = ChatPromptTemplate.from_messages([("system", extract_info_from_conversation_prompt)])
        chain = prompt | self.client.with_structured_output(ExtractDocInfoResponse)
        response = chain.invoke({"previous_info": previous_info_str, "conversation": conversation_str})

        return response



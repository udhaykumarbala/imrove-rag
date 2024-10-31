from .base import BaseLLM
import openai
from typing import List, Dict, Any
from openai import OpenAI
import json

class OpenAIHandler(BaseLLM):
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)  # Initialize client here with API key
        
    def generate_response(self, prompt: str, context: List[Dict[str, str]] = None) -> str:
        messages = []
        if context:
            messages.extend([{"role": msg["role"], "content": msg["content"]} for msg in context])
        messages.append({"role": "user", "content": prompt})
        
        response = self.client.chat.completions.create(  # Use self.client instead of creating new client
            model="gpt-4o",
            messages=messages,
            temperature=0.7,
        )
        return response.choices[0].message.content
    
    def extract_document_info(self, text: str) -> Dict[str, str]:
        prompt = """Extract the following information from the loan document text.Add user consent to add the information to the knowledge base as a field called consent mentioned as boolean.  If any information is missing, mark it as "MISSING":
        - Company Name
        - Loan Plans (with details)
        - Service Areas
        - Credit Score Requirements
        - Loan Minimum Amount
        - Loan Maximum Amount
        - LTV (Loan-to-Value ratio)
        - Application Requirements
        - Guidelines
        - Contact Information (Person, Phone, Email)
        - Property Types
        - Interest Rates
        - Points Charged
        - Liquidity Requirements
        - LTC (Loan-to-Cost ratio)
        - DSCR Minimum (Debt Service Coverage Ratio)
        - Loan Term
        - Amortization
        - Construction (yes/no)
        - Value Add (Yes/no)
        - Personal Gauranty? (yes/no/partial)

        

        Add a field called message which is a markdown formatted response to the user showing the Information extracted and asking for the required information in a polite manner if any information is missing and ask if they would proceed to add the information to the knowledge base.

        Format the response as a JSON object."""
        
        messages = [
            {"role": "user", "content": f"{prompt}\n\nText: {text}"}
        ]
        
        response = self.client.chat.completions.create(  # Use self.client here too
            model="gpt-4o",
            messages=messages,
            temperature=0
        )
        
        content = response.choices[0].message.content
        content = content.replace('```json\n', '').replace('\n```', '')
        response_dict = json.loads(content)  # Use json.loads instead of eval
        
        # Flatten any nested dictionaries to strings
        flattened_dict = {
            k: json.dumps(v) if isinstance(v, dict) else str(v)
            for k, v in response_dict.items()
        }

        
        return flattened_dict
    
    def extract_document_info_from_conversation(self, prompt: str, conversation: List[Dict[str, str]], previous_info: Dict[str, str]) -> Dict[str, str]:
        # Format previous info as a readable string
        previous_info_str = json.dumps(previous_info, indent=2)
        
        system_prompt = f"""
        Extract the information from the conversation and update/merge with the previous information.
        
        Previous information:
        {previous_info_str}
        
        Add user consent to add the information to the knowledge base as a field called consent mentioned as boolean.
        If any information is missing, mark it as "MISSING":
        - Company Name
        - Loan Plans (with details)
        - Service Areas
        - Credit Score Requirements
        - Loan Minimum Amount
        - Loan Maximum Amount
        - LTV (Loan-to-Value ratio)
        - Application Requirements
        - Guidelines
        - Contact Information (Person, Phone, Email)
        - Property Types
        - Interest Rates
        - Points Charged
        - Liquidity Requirements
        - LTC (Loan-to-Cost ratio)
        - DSCR Minimum (Debt Service Coverage Ratio)
        - Loan Term
        - Amortization
        - Construction (yes/no)
        - Value Add (Yes/no)
        - Personal Gauranty? (yes/no/partial)

        Add a field called message which is a markdown formatted response to the user showing the Information extracted and asking for the required information in a polite manner if any information is missing and ask if they would like to add or update the information to the knowledge base. Start the message like the "information is added to the knowledge base" in a more natural tone according to the current user's message.

        If the user asking for any explanation or any other information, add only the message field in the response and give proper formatted explanation, it is not necessary to give extracted information in the message field unless answering the user's question needs it.

        Format the response as a JSON object."""

        messages = [
            {"role": "system", "content": system_prompt}
        ]

        # Add conversation history
        if conversation:
            for msg in conversation:
                messages.append({
                    "role": msg["role"],
                    "content": str(msg["content"])  # Ensure content is string
                })
        
        # Add current prompt
        messages.append({"role": "user", "content": prompt})
        
        response = self.client.chat.completions.create(
            model="gpt-4o",  # Fixed typo in model name from "gpt-4o" to "gpt-4"
            messages=messages,
            temperature=0,
            response_format={ "type": "json_object" } 
        )
        
        content = response.choices[0].message.content
        print(f"🔥llm response: {content}")
        if content.startswith('```json'):
            content = content.replace('```json\n', '').replace('\n```', '')
        print("\n\n success")
        response_dict = json.loads(content)
        print("\n\n success2")
        # Flatten any nested dictionaries to strings
        flattened_dict = {
            k: json.dumps(v) if isinstance(v, dict) else str(v)
            for k, v in response_dict.items()
        }
        
        return flattened_dict
    
from openai import OpenAI
import logging
import base64
import os
from typing import List, Dict
from config import settings
from langchain_openai import ChatOpenAI
from langchain_core.utils.function_calling import convert_to_openai_function
from langchain_core.prompts import ChatPromptTemplate
from langchain.output_parsers.openai_functions import PydanticOutputFunctionsParser

from models.llm import *
from utils.prompt import *

class XAIVision:
    def __init__(self):
        self.client = OpenAI(
            base_url="https://api.x.ai/v1", 
            api_key=settings.XAI_API_KEY,
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

class XAIEmbedding():
    def __init__(self):
        self.client = OpenAI(
            base_url="https://api.x.ai/v1", 
            api_key=settings.XAI_API_KEY)
        self.model = "v1"
        self.logger = logging.getLogger(__name__)

    def create_embedding(self, text):
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
                encoding_format="float"
            )
            return response.data[0].embedding
        except Exception as e:
            self.logger.error(f"Error creating embedding: {str(e)}")
            raise e

class XAICompletion:
    def __init__(self):
        self.model = ChatOpenAI(
                model="grok-beta", 
                temperature=0, 
                timeout=None, 
                max_retries=3, 
                max_tokens=None, 
                base_url="https://api.x.ai/v1", 
                api_key=settings.XAI_API_KEY
            )
        self.logger = logging.getLogger(__name__)

    # upload
    def ingest_document(self, document_text: str):
        try: 
            prompt = ChatPromptTemplate.from_messages([("system", data_extraction_prompt)])
            chain = prompt | self.model.with_structured_output(UploadDocument)
            response = chain.invoke({"document_content": document_text})
            return response.model_dump()
        except Exception as e:
            self.logger.error(f"Error ingesting document: {str(e)}")
            raise e

    def check_relevance(self, document_text: str):
        prompt = ChatPromptTemplate.from_messages([("system", check_relevance_prompt)])
        chain = prompt | self.model.with_structured_output(CheckRelevance)
        response = chain.invoke({"document_content": document_text})
        return response.model_dump()

    def analyze_intent(self, conversation: List[Dict[str, str]], message: str):

        recent_messages = conversation[-10:] if conversation else []
        conversation_payload = [("system", intent_anlyse_prompt)]

        if recent_messages:
            conversation_payload.extend([(msg["role"], msg["content"]) for msg in recent_messages])
        
        conversation_payload.append(("user", message))

        prompt = ChatPromptTemplate.from_messages(conversation_payload)
        chain = prompt | self.model.with_structured_output(AnalyzeIntent)
        response = chain.invoke({})
        return response.model_dump()

    # upload chat 
    def chat_with_document(self, user_message: str, conversation:  List[Dict[str, str]], document_info: Dict[str, str]):
        try:
            conversation_payload = [("system", data_extraction_from_chat_prompt)]

            if conversation:
                conversation_payload.extend([(msg["role"], msg["content"]) for msg in conversation])

            conversation_payload.append(("user", user_message))

            prompt = ChatPromptTemplate.from_messages(conversation_payload)
            chain = prompt | self.model.with_structured_output(UploadChat)
            response = chain.invoke({"extracted_info": document_info})
            return response.model_dump()

        except Exception as e:
            self.logger.error(f"Error chatting with document: {e}")
            return {}

    # kv chat
    def query_from_chat(self, message:str, conversation: List[Dict[str, str]]):
        try:
            recent_messages = conversation[-10:] if conversation else []
            conversation_payload = [("system", features_from_chat_prompt)]

            if recent_messages:
                conversation_payload.extend([(msg["role"], msg["content"]) for msg in recent_messages])

            conversation_payload.append(("user", message))

            prompt = ChatPromptTemplate.from_messages(conversation_payload)
            chain = prompt | self.model.with_structured_output(FeaturesFromChat)
            response = chain.invoke({"messages": conversation_payload})
            response = response.model_dump()

            query = self._construct_mongo_query(response.get("filters", []))
            return query

        except Exception as e:
            self.logger.error(f"Error extracting features from chat: {e}")
            return {}

    # kv chat
    def generate_response(self, intent: str, message: str, conversation: List[Dict[str, str]], kb_mongo_result: str, kb_pinecone_result: str):
        try:
            conversation_payload = [("system", response_generation_prompt)]
            conversation_payload.extend([(msg["role"], msg["content"]) for msg in conversation])
            conversation_payload.append(("user", message))

            prompt = ChatPromptTemplate.from_messages(conversation_payload)
            chain = prompt | self.model.with_structured_output(Response)
            response = chain.invoke({"intent": intent, "kb_mongo_result": kb_mongo_result, "kb_pinecone_result": kb_pinecone_result})
            return response.model_dump()

        except Exception as e:
            self.logger.error(f"Error generating response: {e}")
            return {}

    def _construct_mongo_query(self, filters):
        regular_conditions = {}
        text_search = None

        for condition in filters:
            field = condition["field"]
            operator = condition["operator"]
            value = condition["value"]
            
            if field == "service_areas":
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

        print('regular_conditions', regular_conditions)
        return regular_conditions
        
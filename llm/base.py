from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseLLM(ABC):
    @abstractmethod
    def generate_response(self, prompt: str, context: List[Dict[str, str]] = None) -> str:
        pass
    
    @abstractmethod
    def extract_document_info(self, text: str) -> Dict[str, Any]:
        pass
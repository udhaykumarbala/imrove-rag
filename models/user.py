from datetime import datetime
from typing import Optional
from pymongo import MongoClient
from bson import ObjectId
from config import settings

class User:
    def __init__(self, email: str, name: Optional[str] = None, user_id: Optional[str] = None, created: Optional[datetime] = None):
        self.id = user_id or str(ObjectId())
        self.email = email
        self.name = name
        self.created = created or datetime.utcnow()

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
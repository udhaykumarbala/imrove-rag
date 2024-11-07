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

class UserStore:
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

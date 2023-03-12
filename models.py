from bson import ObjectId
from pydantic import BaseModel, Field, validator

from typing import Optional


# for handling mongo ObjectIds
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")


# user model
class User(BaseModel):
    uid: str
    img: Optional[str] = None
    role: Optional[str] = "public"

    @validator("role")
    def constrain_role(cls, v):
        role = v.lower()
        if role not in ["public", "club", "cc", "slc", "slo"]:
            raise ValueError("Invalid role!")
        return role

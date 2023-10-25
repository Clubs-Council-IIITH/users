import re

from bson import ObjectId
from pydantic import field_validator, BaseModel
from pydantic_core import core_schema
from typing import Any, Optional

# for validating phone numbers
PHONE_REGEX = r"(\+\d{1,3}\s?)?((\(\d{3}\)\s?)|(\d{3})(\s|-?))(\d{3}(\s|-?))(\d{4})(\s?(([E|e]xt[:|.|]?)|x|X)(\s?\d+))?"


# for handling mongo ObjectIds
class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler):
        return core_schema.union_schema(
            [
                # check if it's an instance first before doing any further work
                core_schema.is_instance_schema(ObjectId),
                core_schema.no_info_plain_validator_function(cls.validate),
            ],
            serialization=core_schema.to_string_ser_schema(),
        )

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")


# user model
class User(BaseModel):
    uid: str
    img: Optional[str] = None
    role: Optional[str] = "public"
    phone: Optional[str] = None

    @field_validator("uid", mode="before")
    @classmethod
    def transform_uid(cls, v):
        return v.lower()

    @field_validator("role")
    @classmethod
    def constrain_role(cls, v):
        role = v.lower()
        if role not in ["public", "club", "cc", "slc", "slo"]:
            raise ValueError("Invalid role!")
        return role

    @field_validator("phone")
    @classmethod
    def constrain_phone(cls, v):
        phone = v
        if (phone is not None) and (not re.match(PHONE_REGEX, phone)):
            raise ValueError("Invalid phone number!")
        return phone

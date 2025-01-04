"""
Data Models for Users Microservice

This file decides what and how a User's information is stored in its MongoDB document.
It defines User model for the same purpose.
"""

from typing import Any, Optional

import phonenumbers
from bson import ObjectId
from pydantic import BaseModel, field_validator
from pydantic_core import core_schema


# for handling mongo ObjectIds
class PyObjectId(ObjectId):
    """
    MongoDB ObjectId handler

    This class contains clasmethods to validate and serialize ObjectIds.
    ObjectIds of documents under the Clubs collection are stored under the 'id' field.
    """

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler):
        """
        Defines custom schema for Pydantic validation

        This method is used to define the schema for the Pydantic model.

        Args:
            source_type (Any): The source type.
            handler: The handler.

        Returns:
            dict: The schema for the Pydantic model.
        """

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
        """
        Validates the given ObjectId

        Args:
            v (Any): The value to validate.

        Returns:
            ObjectId: The validated ObjectId.

        Raises:
            ValueError: If the given value is not a valid ObjectId.
        """
        
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        """
        Generates JSON schema

        This method is used to generate the JSON schema for the Pydantic model.

        Args:
            field_schema (dict): The field schema.
        """

        field_schema.update(type="string")


# user model
class User(BaseModel):
    """
    Model for users information

    This model defines the structure of a user's information.

    Attributes:
        uid (str): The user's unique identifier.
        img (Optional[str]): The user's profile picture URL.
        role (Optional[str]): The user's role.
        phone (Optional[str]): The user's phone number.
    """

    uid: str
    img: Optional[str] = None
    role: Optional[str] = "public"
    phone: Optional[str] = None

    # field validators
    @field_validator("uid", mode="before")
    @classmethod
    # this method transforms user's uid to lowercase
    def transform_uid(cls, v):
        return v.lower()

    @field_validator("role")
    @classmethod
    def constrain_role(cls, v):
        """
        Role constraint

        This method checks if the given role is valid.
        Role is valid if it is either "public", "club", "cc", "slc", or "slo".

        Inputs:
            v (str): The role to validate.

        Returns:
            str: The validated role.

        Raises:
            ValueError: If the given role is not valid.
        """

        role = v.lower()
        if role not in ["public", "club", "cc", "slc", "slo"]:
            raise ValueError("Invalid role!")
        return role

    @field_validator("phone")
    @classmethod
    def constrain_phone(cls, v):
        """
        Phone number validator

        This method validates the given phone number by the user.
        It validates according to the Indian phone number format.

        Inputs:
            v (str): The phone number to validate.

        Returns:
            str: The validated phone number. without country code.

        Raises:
            ValueError: If the given phone number is not valid.
        """
        
        if v is None or v == "":
            return None
        try:
            phone = phonenumbers.parse(v, "IN")
            if not phonenumbers.is_valid_number(phone):
                raise ValueError("Invalid phone number!")
            return phonenumbers.format_number(
                phone, phonenumbers.PhoneNumberFormat.INTERNATIONAL
            )
        except phonenumbers.phonenumberutil.NumberParseException:
            raise ValueError("Invalid phone number!")
        except Exception as e:
            raise ValueError(str(e))

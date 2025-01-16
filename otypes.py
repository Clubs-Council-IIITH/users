"""
Types and Inputs
"""
import json
from functools import cached_property
from typing import Dict, Optional, Union

import strawberry
from strawberry.fastapi import BaseContext
from strawberry.types import Info as _Info
from strawberry.types.info import RootValueType

from models import PyObjectId, User


# custom context class
class Context(BaseContext):
    """
    Class provides user metadata and cookies from request headers, has methods for doing this.
    """
    @cached_property
    def user(self) -> Union[Dict, None]:
        
        if not self.request:
            return None

        user = json.loads(self.request.headers.get("user", "{}"))
        return user

    @cached_property
    def cookies(self) -> Union[Dict, None]:

        if not self.request:
            return None

        cookies = json.loads(self.request.headers.get("cookies", "{}"))
        return cookies


"""A scalar Type for serializing PyObjectId, used for id field"""
Info = _Info[Context, RootValueType]

# serialize PyObjectId as a scalar type
PyObjectIdType = strawberry.scalar(
    PyObjectId, serialize=str, parse_value=lambda v: PyObjectId(v)
)


# user profile type
@strawberry.type
class ProfileType:
    """
     Type used for returning user details stored in LDAP server.
    """
    firstName: str
    lastName: str
    email: str
    gender: str | None
    batch: str | None
    stream: str | None
    rollno: str | None


# authenticated user details type
@strawberry.experimental.pydantic.type(model=User)
class UserMetaType:
    """
    Type used for returning user details stored in the database.
    """
    uid: strawberry.auto
    role: strawberry.auto
    img: strawberry.auto
    phone: strawberry.auto


# user id input
@strawberry.input
class UserInput:
    """
     Input used to take user id as input.
    """
    uid: str


# user role input
@strawberry.input
class RoleInput:
    """
    Input used to take user id and role as input.
    """
    uid: str
    role: str
    inter_communication_secret: Optional[str] = None


# user phone input type
@strawberry.input
class PhoneInput:
    """
    Input used to take user id and phone number as input.
    """
    uid: str
    phone: str


# user data input
@strawberry.input
class UserDataInput:
    """
    Input used to take user id, image and phone number as input.
    """
    uid: str
    img: Optional[str] = None
    phone: Optional[str]

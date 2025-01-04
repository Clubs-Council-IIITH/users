"""
Types and Inputs

It contains both Inputs and Types for taking inputs and returning outputs.
It also contains the Context class which is used to pass the user details to the resolvers.

Types:
    Info : used to pass the user details to the resolvers.
    PyObjectId : used to return ObjectId of a document.
    ProfileType : used to return first name, last name, email, gender, batch, roll no and stream of the user, this is used for LDAP authentication.
    UserMetaType : used to return all the details of a user.


Inputs:
    UserInput : used to input only uid(User ID)
    RoleInput : used to input uid and role of the user along with the intercommunication secret(Optional)
    ImageInput : used to input uid and photo of the user
    UserDataInput : used to input uid, image(Optional) and phone no(Optional) of the user
    
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
    To pass user details

    This class is used to pass the user details to the resolvers.
    It will be used through the Info type.
    """

    @cached_property
    def user(self) -> Union[Dict, None]:
        """
        Returns User Details
        
        It will be used in the resolvers to check the user details.

        Returns:
            user (Dict): Contains User Details.
        """
        
        if not self.request:
            return None

        user = json.loads(self.request.headers.get("user", "{}"))
        return user

    @cached_property
    def cookies(self) -> Union[Dict, None]:
        """
        Returns Cookies Details

        It will be used in the resolvers to check the cookies details.

        Returns:
            cookies (Dict): Contains Cookies Details.
        """

        if not self.request:
            return None

        cookies = json.loads(self.request.headers.get("cookies", "{}"))
        return cookies


# custom info type
Info = _Info[Context, RootValueType]

# serialize PyObjectId as a scalar type
PyObjectIdType = strawberry.scalar(
    PyObjectId, serialize=str, parse_value=lambda v: PyObjectId(v)
)


# user profile type
@strawberry.type
class ProfileType:
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
    uid: strawberry.auto
    role: strawberry.auto
    img: strawberry.auto
    phone: strawberry.auto


# user id input
@strawberry.input
class UserInput:
    uid: str


# user role input
@strawberry.input
class RoleInput:
    uid: str
    role: str
    inter_communication_secret: Optional[str] = None


# user img input # TODO: deprecate
@strawberry.input
class ImageInput:
    uid: str
    img: str


# user data input
@strawberry.input
class UserDataInput:
    uid: str
    img: Optional[str] = None
    phone: Optional[str]

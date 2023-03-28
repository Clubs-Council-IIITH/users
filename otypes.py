import json
import strawberry

from strawberry.fastapi import BaseContext
from strawberry.types import Info as _Info
from strawberry.types.info import RootValueType

from typing import Union, Dict
from functools import cached_property

from models import PyObjectId, User


# custom context class
class Context(BaseContext):
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
    img: str


# authenticated user details type
@strawberry.experimental.pydantic.type(model=User)
class UserMetaType:
    uid: strawberry.auto
    role: strawberry.auto


# user input type
@strawberry.input
class UserInput:
    uid: str


@strawberry.input
class AuthInput:
    uid: str
    secret: str

# user role input type
@strawberry.input
class RoleInput:
    uid: str
    role: str


# user img input type
@strawberry.input
class ImageInput:
    uid: str
    img: str

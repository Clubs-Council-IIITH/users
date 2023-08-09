import json
import strawberry

from strawberry.fastapi import BaseContext
from strawberry.types import Info as _Info
from strawberry.types.info import RootValueType

from functools import cached_property
from typing import Union, Dict, Optional

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
    gender: str | None
    batch: str | None
    stream: str | None


# authenticated user details type
@strawberry.experimental.pydantic.type(model=User)
class UserMetaType:
    uid: strawberry.auto
    role: strawberry.auto
    img: strawberry.auto
    phone: strawberry.auto


# user input type
@strawberry.input
class UserInput:
    uid: str


# user role input type
@strawberry.input
class RoleInput:
    uid: str
    role: str


# user img input type # TODO: deprecate
@strawberry.input
class ImageInput:
    uid: str
    img: str


# user data input type
@strawberry.input
class UserDataInput:
    uid: str
    img: Optional[str]
    phone: Optional[str]

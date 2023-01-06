import ldap
import strawberry

from typing import Optional
from fastapi.encoders import jsonable_encoder

from db import db

# import all models and types
from models import User
from otypes import Info, UserInput, ProfileType, UserMetaType

# instantiate LDAP client
LDAP = ldap.initialize("ldap://ldap.iiit.ac.in")


# get user profile from LDAP
# if profileInput is passed, use the provided uid
# else return the profile of currently logged in user
@strawberry.field
def getProfile(userInput: Optional[UserInput], info: Info) -> ProfileType:
    user = info.context.user

    # if input uid is provided, use it
    # else use current logged in user's uid (if logged in)
    target = None
    if userInput:
        target = userInput.uid
    if user and (target is None):
        target = user.get("uid", None)

    # error out if querying uid is null
    if target is None:
        raise Exception("Can not query a null uid! Log in or provide an uid as input.")

    # query LDAP for user profile
    result = LDAP.search_s(
        "ou=Users,dc=iiit,dc=ac,dc=in",
        ldap.SCOPE_SUBTREE,
        filterstr=f"(uid={target})",
    )

    # error out if LDAP query fails
    if not result:
        raise Exception("Could not find user profile in LDAP!")

    # extract profile attributes
    result = result[0][1]
    firstName = result["givenName"][0].decode()
    lastName = result["sn"][0].decode()
    email = result["mail"][0].decode()

    profile = ProfileType(
        firstName=firstName,
        lastName=lastName,
        email=email,
    )

    return profile


@strawberry.field
def getUserMeta(userInput: UserInput) -> UserMetaType:
    user = jsonable_encoder(userInput)

    # query database for user
    found_user = db.users.find_one({"uid": user["uid"]})

    # if user doesn't exist, add to database
    if found_user:
        found_user = User.parse_obj(found_user)
    else:
        found_user = User(uid=user["uid"])
        db.users.insert_one(jsonable_encoder(found_user))

    return UserMetaType.from_pydantic(found_user)


# register all queries
queries = [
    getProfile,
    getUserMeta,
]

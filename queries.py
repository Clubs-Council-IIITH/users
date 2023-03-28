import ldap
import strawberry
from os import getenv

from typing import Optional
from fastapi.encoders import jsonable_encoder

from db import db

# import all models and types
from models import User
from otypes import Info, UserInput, AuthInput, ProfileType, UserMetaType

# instantiate LDAP client
LDAP = ldap.initialize("ldap://ldap.iiit.ac.in")

def find_user(uid):
    # query database for user
    found_user = db.users.find_one({"uid": uid})

    # if user doesn't exist, add to database
    if found_user:
        found_user = User.parse_obj(found_user)
    else:
        found_user = User(uid=uid)
        db.users.insert_one(jsonable_encoder(found_user))
    
    return found_user


# get user profile from LDAP
# if profileInput is passed, use the provided uid
# else return the profile of currently logged in user
@strawberry.field
def userProfile(userInput: Optional[UserInput], info: Info) -> ProfileType:
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
    
    found_user = find_user(target)

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
    img = found_user.img

    if img is None:
        img = "https://t3.ftcdn.net/jpg/05/16/27/58/360_F_516275801_f3Fsp17x6HQK0xQgDQEELoTuERO4SsWV.jpg"

    profile = ProfileType(
        firstName=firstName,
        lastName=lastName,
        email=email,
        img = img
    )

    return profile


# get user metadata (uid, role, etc.) from local database
@strawberry.field
def userMeta(authInput: Optional[AuthInput], info: Info) -> UserMetaType:
    secret = authInput.secret
    if secret != getenv("AUTH_SECRET", default="default"):
        raise Exception("You cannot access this Query!!")

    user = info.context.user

    # if input uid is provided, use it
    # else use current logged in user's uid (if logged in)
    target = None
    if authInput:
        target = authInput.uid
    if user and (target is None):
        target = user.get("uid", None)

    # error out if querying uid is null
    if target is None:
        raise Exception("Can not query a null uid! Log in or provide an uid as input.")

    found_user = find_user(target)

    return UserMetaType.from_pydantic(found_user)


# register all queries
queries = [
    userProfile,
    userMeta,
]

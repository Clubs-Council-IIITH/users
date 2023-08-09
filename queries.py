import re
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
def userProfile(userInput: Optional[UserInput], info: Info) -> ProfileType | None:
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
        return None
        # raise Exception(
        #     "Can not query a null uid! Log in or provide an uid as input.")

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
    dn = result[0][0]
    ous = re.findall(r"ou=\w.*?,", dn)  # get list of OUs the current DN belongs to
    result = result[0][1]
    if "cn" in result.keys():
        fullNameList = result["cn"][0].decode().split()
        firstName = fullNameList[0]
        lastName = " ".join(fullNameList[1:])
    else:
        firstName = result["givenName"][0].decode()
        lastName = result["sn"][0].decode()
    email = result["mail"][0].decode()

    # extract optional attributes
    gender = None
    if "gender" in result:
        gender = result["gender"][0].decode()

    batch = None
    if len(ous) > 1:
        # extract batch code from OUs
        batch = re.sub(r"ou=(.*)?,", r"\1", ous[1])
        # remove the 'dual' suffix if it exists
        batch = re.sub(r"dual$", "", batch, flags=re.IGNORECASE)

    stream = None
    if len(ous) > 0:
        # extract stream code from OUs
        stream = re.sub(r"ou=(.*)?,", r"\1", ous[0])

    profile = ProfileType(
        firstName=firstName,
        lastName=lastName,
        email=email,
        gender=gender,
        batch=batch,
        stream=stream,
    )

    return profile


# get user metadata (uid, role, etc.) from local database
@strawberry.field
def userMeta(userInput: Optional[UserInput], info: Info) -> UserMetaType | None:
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
        return None
        # raise Exception(
        #     "Can not query a null uid! Log in or provide an uid as input.")

    # query database for user
    found_user = db.users.find_one({"uid": target})

    # if user doesn't exist, add to database
    if found_user:
        found_user = User.parse_obj(found_user)
    else:
        found_user = User(uid=target)
        db.users.insert_one(jsonable_encoder(found_user))

    return UserMetaType.from_pydantic(found_user)


# register all queries
queries = [
    userProfile,
    userMeta,
]

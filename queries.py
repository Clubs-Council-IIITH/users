import os
from typing import List, Optional

import strawberry
from fastapi.encoders import jsonable_encoder

from db import db

# import all models and types
from models import User
from otypes import Info, ProfileType, UserInput, UserMetaType
from utils import get_profile, ldap_search

inter_communication_secret_global = os.getenv("INTER_COMMUNICATION_SECRET")


# get user profile from LDAP
# if profileInput is passed, use the provided uid
# else return the profile of currently logged in user
@strawberry.field
def userProfile(
    userInput: Optional[UserInput], info: Info
) -> ProfileType | None:
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
    result = ldap_search(f"(uid={target})")

    # error out if LDAP query fails
    if not result:
        print(f"Could not find user profile for {target} in LDAP!")
        raise Exception("Could not find user profile in LDAP!")

    return get_profile(result[-1])  # single profile


# get user metadata (uid, role, etc.) from local database
@strawberry.field
def userMeta(
    userInput: Optional[UserInput], info: Info
) -> UserMetaType | None:
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

    target = target.lower()

    # query database for user
    found_user = db.users.find_one({"uid": target})

    # if user doesn't exist, add to database
    if found_user:
        found_user = User.model_validate(found_user)
    else:
        found_user = User(uid=target)
        db.users.insert_one(jsonable_encoder(found_user))

    found_user.uid = target

    if not user or (
        user["role"] not in ["cc", "slo", "slc", "club"]
        and user["uid"] != target
    ):
        # if user is not authorized to see phone number, hide the phone number
        found_user.phone = None

    return UserMetaType.from_pydantic(found_user)


# get all users belonging to the input role
@strawberry.field
def usersByRole(
    info: Info, role: str, inter_communication_secret: str | None = None
) -> List[UserMetaType]:
    user = info.context.user

    if user:
        if user["role"] in [
            "cc",
        ]:
            inter_communication_secret = inter_communication_secret_global

    if inter_communication_secret != inter_communication_secret_global:
        raise Exception("Authentication Error! Invalid secret!")

    users = db.users.find({"role": role})
    return [
        UserMetaType.from_pydantic(User.model_validate(user)) for user in users
    ]


@strawberry.field
def usersByBatch(batch_year: int) -> List[ProfileType]:
    if batch_year < 18 or batch_year > 100:
        return []

    prefixes = ["ug2k", "ms2k", "mtech2k", "pgssp2k", "phd2k"]

    full_ous = [prefix + str(batch_year) for prefix in prefixes]
    full_ous.append(f"le2k{batch_year + 1}")
    full_ous.append(f"ug2k{batch_year}dual")

    filterstr = f"(&(|{''.join(f'(ou:dn:={ou})' for ou in full_ous)})(uid=*))"

    result = ldap_search(filterstr)

    # error out if LDAP query fails
    if not result:
        print(
            f"Could not find user profiles for batch 2k{batch_year} in LDAP!"
        )
        raise Exception(
            f"Could not find user profiles for batch 2k{batch_year} in LDAP!"
        )

    # use filter() to get non None values
    return [
        get_profile(user_result) for user_result in result
    ]  # single profile


# register all queries
queries = [
    userProfile,
    userMeta,
    usersByRole,
    usersByBatch,
]

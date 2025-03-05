"""
Query Resolvers
"""

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


@strawberry.field
def userProfile(
    userInput: Optional[UserInput], info: Info
) -> ProfileType | None:
    """
    User Information from LDAP

    This method is used to get the profile of a user from IIITH server
    directory using LDAP.
    Searched on the basis of the uid given as input or the currently logged
    user's uid.
    Accessible to all users.

    Args:
        userInput (UserInput): Contains the uid of the user. Optional as if
                            not passed uses the current logged in user's info.
        info (Info): Contains the user details.

    Returns:
        Contains the profile of the user.

    Raises:
        Exception: Could not find user profile in LDAP.
    """

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
    """
    User information from database

    This method is used to get the metadata of a user from database.
    Searched on the basis of the uid given as input or the currently logged
    user's uid.
    It hides the phone number only for public users.

    Args:
        userInput (UserInput): Contains the uid of the user. Optional as if
                            not passed uses the current logged in user's info.
        info (Info): Contains the user details.

    Returns:
        Contains the metadata of the user.
    """

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
    """
    This method is used to get the metadata of all users belonging to the
    given input role.

    Args:
        role (str): The role of the user.
        inter_communication_secret (str): The secret used to authenticate
                                          the request. Defaults to None.

    Returns:
        Contains the metadata of the users.

    Raises:
        Exception: Authentication Error! Invalid secret!
    """
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
    """
    This method is used to get the profiles
    of all users belonging to the
    given input batch year, from UG, MS,
    MTECH, PG and PHD batches.

    Args:
        batch_year (int): The batch year of the user.

    Returns:
        Contains the profiles of the users.

    Raises:
        Exception: Could not find user profiles
                    for given batch year in LDAP!
    """
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


# get all users in the given list of uids
@strawberry.field
def usersByList(
    info: Info, userInputs: List[UserInput]
) -> List[Optional[ProfileType]]:
    """
    This method is used to get the profiles of all
    users belonging to the input array of uids.

    Args:
        userInputs (List[UserInput]): The list of
                                        uids of the users.
        info (Info): Contains the user details.

    Returns:
        Contains the profiles of the users.
    """

    profiles = []

    filterstr = (
        f"(|{''.join(f'(uid={userInput.uid})' for userInput in userInputs)})"
    )
    results: List = ldap_search(filterstr)

    # Make a list of successful profiles
    resultUids = [result[1]["uid"][0].decode() for result in results]

    for userInput in userInputs:
        uid = userInput.uid
        if uid in resultUids:  # If we get a result for this uid
            index = resultUids.index(uid)
            profiles.append(get_profile(results[index]))
            results.pop(index)  # Remove uid to speed up search time
            resultUids.pop(index)
        else:
            profiles.append(None)

    return profiles


# register all queries
queries = [
    userProfile,
    userMeta,
    usersByRole,
    usersByBatch,
    usersByList,
]

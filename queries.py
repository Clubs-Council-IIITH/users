"""
Query Resolvers

This file contains the 3 different query resolvers.
each resolves a different query, each providing a different set of information.

Resolvers:
    userProfile: Returns the profile of a user from LDAP.
    userMeta: Returns the metadata of a user from database.
    usersByRole: Returns the users of a specific role.
"""

import os
import re
from typing import List, Optional

import ldap
import strawberry
from fastapi.encoders import jsonable_encoder

from db import db

# import all models and types
from models import User
from otypes import Info, ProfileType, UserInput, UserMetaType

inter_communication_secret_global = os.getenv("INTER_COMMUNICATION_SECRET")

# instantiate LDAP client
LDAP = ldap.initialize("ldap://ldap.iiit.ac.in")


@strawberry.field
def userProfile(
    userInput: Optional[UserInput], info: Info
) -> ProfileType | None:
    """
    Get user profile from LDAP

    This method is used to get the profile of a user from IIITH server directory using LDAP.
    The profile of a user includes first name, last name, email, gender, batch, roll no and stream.
    It is searched on the basis of uid if given as input or the currently logged in user's uid(from Info).

    Inputs:
        userInput (UserInput): Contains the uid of the user.(Optional)
        info (Info): Contains the user details.

    Returns:
        ProfileType: Contains the profile of the user.

    Accessibility:
        Public

    Raises Exception:
        Could not find user profile : If the user is not found in the LDAP server.
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
    global LDAP
    try:
        result = LDAP.search_s(
            "ou=Users,dc=iiit,dc=ac,dc=in",
            ldap.SCOPE_SUBTREE,
            filterstr=f"(uid={target})",
        )
    except ldap.SERVER_DOWN:
        # Reconnect to LDAP server and retry the search
        LDAP = ldap.initialize("ldap://ldap.iiit.ac.in")
        result = LDAP.search_s(
            "ou=Users,dc=iiit,dc=ac,dc=in",
            ldap.SCOPE_SUBTREE,
            filterstr=f"(uid={target})",
        )

    # error out if LDAP query fails
    if not result:
        print(f"Could not find user profile for {target} in LDAP!")
        raise Exception("Could not find user profile in LDAP!")

    # extract profile attributes
    dn = result[-1][0]
    ous = re.findall(
        r"ou=\w.*?,", dn
    )  # get list of OUs the current DN belongs to
    result = result[-1][1]
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

    rollno = None
    if "uidNumber" in result:
        rollno = result["uidNumber"][0].decode()
    elif "sambaSID" in result:
        rollno = result["sambaSID"][0].decode()

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
        rollno=rollno,
    )

    return profile


# get user metadata (uid, role, etc.) from local database
@strawberry.field
def userMeta(
    userInput: Optional[UserInput], info: Info
) -> UserMetaType | None:
    """
    User information from database

    This method is used to get the metadata of a user from database.
    If uid is provided as input then it is used, else the currently logged in user's uid.
    It is used to fetch the user's role, image and phone number.
    It creates a new user in database if a user with the gien uid is not found.
    It hides the phone number for users with partial access.

    Inputs:
        userInput (UserInput): Contains the uid of the user.(Optional)
        info (Info): Contains the user details.

    Accessibility:
        Public has partial access
        CC,SLO,SLC,the same club have full access

    Returns:
        UserMetaType: Contains the metadata of the user.
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
    To search users by role

    This method is used to get the metadata of all users belonging to the input role.
    It is used to fetch the user's role, image and phone number.

    Inputs:
        role (str): The role of the user.
        inter_communication_secret (str): The secret used to authenticate the request.

    Returns:
        List[UserMetaType]: Contains the metadata of the users.
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


# register all queries
queries = [
    userProfile,
    userMeta,
    usersByRole,
]

"""
Mutations for Users Microservice
"""

import os

import strawberry
from fastapi.encoders import jsonable_encoder

from db import db
from models import User

# import all models and types
from otypes import Info, RoleInput, UserDataInput

inter_communication_secret = os.getenv("INTER_COMMUNICATION_SECRET")


# update role of user with uid
@strawberry.mutation
def updateRole(roleInput: RoleInput, info: Info) -> bool:
    """
    This method is used to update the role of a user by CC.
    
    Args:
        roleInput (RoleInput): Contains the uid and role of the user.
        info (Info): Contains the user details.
    
    Returns:
        bool: True if the role is updated successfully, False otherwise.

    Raises:
        Exception: Not logged in!
        Exception: Authentication Error! Only admins can assign roles!
        Exception: Authentication Error! Invalid secret!
    """

    user = info.context.user
    if not user:
        raise Exception("Not logged in!")

    roleInputData = jsonable_encoder(roleInput)

    # check if user is admin
    if user.get("role", None) not in ["cc"]:
        raise Exception("Authentication Error! Only admins can assign roles!")

    # check if the secret is correct
    if (
        roleInputData.get("inter_communication_secret", None)
        != inter_communication_secret
    ):
        raise Exception("Authentication Error! Invalid secret!")

    db_user = db.users.find_one({"uid": roleInputData["uid"]})

    # insert if not exists
    if not db_user:
        new_user = User(uid=roleInputData["uid"])
        db.users.insert_one(jsonable_encoder(new_user))

    # update role in database
    db.users.update_one(
        {"uid": roleInputData["uid"]},
        {"$set": {"role": roleInputData["role"]}},
    )

    return True


@strawberry.mutation
def updateUserPhone(userDataInput: UserDataInput, info: Info) -> bool:
    """
    This method is used to update the phone number of a user by the cc and user.

    Args:
        userDataInput (UserDataInput): Contains the uid and phone number of the user.
        info (Info): Contains the user details.

    Returns:
        bool: True if the phone number is updated successfully, False otherwise.

    Raises:
        Exception: Not logged in!
        Exception: Invalid phone number!
        Exception: You are not allowed to perform this action!
    """

    user = info.context.user
    if not user:
        raise Exception("Not logged in!")

    userData = jsonable_encoder(userDataInput)

    # Validate the data by putting in the model
    try:
        User(**userData)
    except Exception:
        raise Exception("Invalid phone number!")

    # check if user has access
    if not (
        user.get("role", None) in ["cc", "club"]
        or user.get("uid", None) == userData["uid"]
    ):
        raise Exception("You are not allowed to perform this action!")

    db.users.update_one(
        {"uid": userData["uid"]},
        {"$set": {"phone": userData["phone"]}},
    )

    return True


@strawberry.mutation
def updateUserData(userDataInput: UserDataInput, info: Info) -> bool:
    """
    Used to update the data of a user by CC and the User

    Args:
        userDataInput (UserDataInput): Contains the uid, image and phone number of the user.
        info (Info): Contains the user details.

    Returns:
        bool: True if the data is updated successfully, False otherwise.

    Raises:
        Exception: Not logged in!
        Exception: You are not allowed to perform this action!
    """

    user = info.context.user
    if not user:
        raise Exception("Not logged in!")

    userData = jsonable_encoder(userDataInput)

    # check if user has access
    if (
        user.get("role", None) not in ["cc"]
        and user.get("uid", None) != userData["uid"]
    ):
        raise Exception("You are not allowed to perform this action!")

    # Validate the data by putting in the model
    User(**userData)

    db.users.update_one(
        {"uid": userData["uid"]},
        {"$set": {"img": userData["img"], "phone": userData["phone"]}},
    )

    return True


# register all mutations
mutations = [
    updateRole,
    updateUserPhone,
    updateUserData,
]

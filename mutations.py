import strawberry

from fastapi.encoders import jsonable_encoder

from db import db

# import all models and types
from otypes import Info, RoleInput, UserDataInput
from models import User


# update role of user with uid
@strawberry.mutation
def updateRole(roleInput: RoleInput, info: Info) -> bool:
    user = info.context.user
    if not user:
        raise Exception("Not logged in!")

    roleInputData = jsonable_encoder(roleInput)

    # check if user is admin
    if user.get("role", None) not in ["cc"]:
        raise Exception("Authentication Error! Only admins can assign roles!")

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
    user = info.context.user
    if not user:
        raise Exception("Not logged in!")

    userData = jsonable_encoder(userDataInput)

    # Validate the data by putting in the model
    try:
        User(**userData)
    except Exception as e:
        raise Exception(f"Invalid data: {e}")

    # check if user has access
    if user.get("role", None) not in ["cc", "club"]:
        raise Exception("You are not allowed to perform this action!")

    db.users.update_one(
        {"uid": userData["uid"]},
        {"$set": {"phone": userData["phone"]}},
    )

    return True


@strawberry.mutation
def updateUserData(userDataInput: UserDataInput, info: Info) -> bool:
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
    try:
        User(**userData)
    except Exception as e:
        raise Exception(f"Invalid data: {e}")

    
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

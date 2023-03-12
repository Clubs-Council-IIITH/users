import strawberry

from fastapi.encoders import jsonable_encoder

from db import db

# import all models and types
from otypes import Info, RoleInput


# update role of user with uid
@strawberry.mutation
def updateRole(roleInput: RoleInput, info: Info) -> bool:
    user = info.context.user
    if not user:
        raise Exception("Not logged in!")

    roleInput = jsonable_encoder(roleInput)

    print("user:", user)
    print("role:", user.get("role", None))

    # check if user is admin
    if user.get("role", None) not in ["cc"]:
        raise Exception("Only admins can assign roles!")

    # update role in database
    db.users.update_one(
        {"uid": roleInput["uid"]},
        {"$set": {"role": roleInput["role"]}},
    )

    return True


# register all mutations
mutations = [
    updateRole,
]

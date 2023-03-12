import strawberry

from fastapi.encoders import jsonable_encoder

from db import db

# import all models and types
from otypes import Info, RoleInput
from models import User


# update role of user with uid
@strawberry.mutation
def updateRole(roleInput: RoleInput, info: Info) -> bool:
    user = info.context.user
    if not user:
        raise Exception("Not logged in!")

    roleInput = jsonable_encoder(roleInput)

    # check if user is admin
    if user.get("role", None) not in ["cc"]:
        raise Exception("Authentication Error! Only admins can assign roles!")

    db_user = db.users.find_one({"uid": roleInput["uid"]})

    # insert if not exists
    if not db_user:
        new_user = User(uid=roleInput["uid"])
        db.users.insert_one(jsonable_encoder(new_user))
    
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

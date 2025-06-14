"""
To run this script inside the container, 
use the following command from outside the scripts directory:

python3 -m scripts.member_no_img
"""

import csv
from datetime import datetime
from os import getenv, makedirs

from pymongo import MongoClient

from utils import ldap_search

MONGO_URI = "mongodb://{}:{}@mongo:{}/".format(
    getenv("MONGO_USERNAME", default="username"),
    getenv("MONGO_PASSWORD", default="password"),
    getenv("MONGO_PORT", default="27107"),
)
MONGO_DATABASE = getenv("MONGO_DATABASE", default="default")
client = MongoClient(MONGO_URI)
db = client[MONGO_DATABASE]

makedirs("reports", exist_ok=True)

current_year = datetime.now().year
# Fetch active clubs
results = db.clubs.find({"state": "active"})
clubs = [result for result in results]
userlist = []

# Process each club
for club in clubs:
    if club["state"] != "active":
        continue
    results = db.members.find({"cid": club["cid"]})
    members = [result for result in results]
    for member in members:
        flag = 0
        for role in member["roles"]:
            if (
                role["end_year"] is None
                or int(role["end_year"]) >= current_year
            ):
                flag = 1
                break
        if flag == 1:
            users = list(db.users.find({"uid": member["uid"]}))
            for user in users:
                if user["img"] is None:
                    if user["uid"] not in userlist:
                        userlist.append(user["uid"])
                    break

userlist = list(set(userlist))  # Remove duplicates
userlist.sort()

# Write results to a CSV file
with open("reports/members_without_images.csv", "w", newline="") as csvfile:
    csvwriter = csv.writer(csvfile)

    # Write the header
    csvwriter.writerow(["email IDs"])

    # Write the data
    for users in userlist:
        result = ldap_search(f"(uid={users})")
        try:
            dn, details = result[-1]
            email = details["mail"][0].decode()
            csvwriter.writerow([email])
        except:
            csvwriter.writerow([f"Could not find email for {users} in LDAP"])
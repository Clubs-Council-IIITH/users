import asyncio
import os
import re
from typing import List
from cachetools import TTLCache

import ldap

# import all models and types
from otypes import ProfileType

# LDAP Host
LDAP_HOST = os.getenv("LDAP_HOST", "ldaps://ldap.iiit.ac.in")
LDAP = ldap.initialize(LDAP_HOST)

# cache ldap_search for 15 days
CACHE_TTL = 15*24*60*60
LDAP_CACHE = TTLCache(maxsize=512, ttl=CACHE_TTL)

async def ldap_search(filterstr: str) -> List[tuple]:
    """
    Fetchs details from LDAP server of user matching the filters.

    Args:
        filterstr (str): LDAP filter string.

    Returns:
        (List[tuple]): List of tuples containing the details of the user.
    """

    # check the cache first
    if filterstr in LDAP_CACHE:
        return LDAP_CACHE[filterstr]
    
    global LDAP
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(
            None,
            lambda: LDAP.search_s(
                "ou=Users,dc=iiit,dc=ac,dc=in",
                ldap.SCOPE_SUBTREE,
                filterstr,
            ),
        )
    except ldap.SERVER_DOWN:
        # Reconnect to LDAP server and retry the search
        LDAP = ldap.initialize(LDAP_HOST)
        result = await loop.run_in_executor(
            None,
            lambda: LDAP.search_s(
                "ou=Users,dc=iiit,dc=ac,dc=in",
                ldap.SCOPE_SUBTREE,
                filterstr,
            ),
        )

    LDAP_CACHE[filterstr] = result
    return result


def get_profile(ldap_result: List) -> ProfileType:
    """
    Fetches user's ProfileType from the result of the request to LDAP server.

    Args:
        ldap_result (List): List of tuples containing the details of the user.

    Returns:
        (otypes.ProfileType): Contains the profile of the user.
    """

    dn, details = ldap_result
    ous = re.findall(
        r"ou=\w.*?,", dn
    )  # get list of OUs the current DN belongs to
    if "cn" in details:
        fullNameList = details["cn"][0].decode().split()
        firstName = fullNameList[0]
        lastName = " ".join(fullNameList[1:])
    elif "givenName" in details and "sn" in details:
        firstName = details["givenName"][0].decode()
        lastName = details["sn"][0].decode()
    else:
        small_fn, small_ln = details["uid"].split(".")
        firstName = small_fn.capitalize()
        lastName = small_ln.capitalize()

    # extract optional attributes
    gender = None
    if "gender" in details:
        gender = details["gender"][0].decode()

    rollno = None
    if "uidNumber" in details:
        rollno = details["uidNumber"][0].decode()
    elif "sambaSID" in details:
        rollno = details["sambaSID"][0].decode()

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

    uid = None
    if "uid" in details:
        uid = details["uid"][0].decode()

    email = None
    if "mail" in details:
        email = details["mail"][0].decode()
    elif uid is not None:
        email = f"{uid}@iiit.ac.in"
    else:
        email = ""

    profile = ProfileType(
        uid=uid,
        firstName=firstName,
        lastName=lastName,
        email=email,
        gender=gender,
        batch=batch,
        stream=stream,
        rollno=rollno,
    )

    return profile

import asyncio
import json
import logging
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import List

try:
    import ldap
except ImportError:
    ldap = None

from cachetools import TTLCache

# import all models and types
from otypes import ProfileType

log = logging.getLogger("users.utils")

# Debug / Dev Mode
DEBUG = os.getenv("GLOBAL_DEBUG", "False").lower() in ("true", "1", "t")

# LDAP Host & Credentials
LDAP_HOST = os.getenv("LDAP_HOST", "ldaps://ldap.iiit.ac.in")
LDAP_USER_X = os.getenv("LDAP_USER_X", os.getenv("USER_X", ""))
LDAP_PASSWORD_X = os.getenv("LDAP_PASSWORD_X", os.getenv("PASSWORD_X", ""))

# Only initialize python-ldap client if not in debug mode or if python-ldap is available
LDAP = None
if not DEBUG and ldap is not None and hasattr(ldap, "initialize"):
    LDAP = ldap.initialize(LDAP_HOST)

# cache ldap_search for 15 days
CACHE_TTL = 15 * 24 * 60 * 60
LDAP_CACHE = TTLCache(maxsize=512, ttl=CACHE_TTL)


def _http_mock_ldap_search_sync(filterstr: str) -> List[tuple]:
    """
    Perform an HTTP search against the mock LDAP server with user-x and password-x headers.
    """
    host = LDAP_HOST
    if not host.startswith(("http://", "https://", "ldap://", "ldaps://")):
        host = f"http://{host}"

    parsed = urllib.parse.urlparse(host)
    scheme = "https" if parsed.scheme in ("https", "ldaps") else "http"
    netloc = parsed.netloc

    # If no port is specified in netloc, default to 389 for ldap URLs or when port is omitted
    if ":" not in netloc:
        if parsed.scheme in ("ldap", "ldaps") or host.startswith(("ldap://", "ldaps://")):
            netloc = f"{netloc}:389"

    path = parsed.path.rstrip("/")
    if not path.endswith("/search"):
        url = f"{scheme}://{netloc}/search"
    else:
        url = f"{scheme}://{netloc}{path}"

    payload = json.dumps({"filter": filterstr}).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
    }
    if LDAP_USER_X:
        headers["user-x"] = LDAP_USER_X
    if LDAP_PASSWORD_X:
        headers["password-x"] = LDAP_PASSWORD_X

    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        err_msg = exc.read().decode("utf-8", errors="replace")
        log.error("Mock LDAP HTTP search failed (%d): %s", exc.code, err_msg)
        raise Exception(f"Mock LDAP search failed: {exc.code} {err_msg}") from exc
    except Exception as exc:
        log.error("Mock LDAP HTTP connection error: %s", exc)
        raise Exception(f"Could not connect to mock LDAP server: {exc}") from exc

    # Convert JSON response to match python-ldap return format:
    # [(dn: str, {attr: [bytes, ...]})]
    formatted_results = []
    for entry in data:
        dn = entry.get("dn", "")
        attrs_raw = entry.get("attrs", {})
        attrs_bytes = {}
        for k, vals in attrs_raw.items():
            encoded_vals = [
                v.encode("utf-8") if isinstance(v, str) else v for v in vals
            ]
            attrs_bytes[k] = encoded_vals
        formatted_results.append((dn, attrs_bytes))

    return formatted_results


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

    # In dev/debug mode, use HTTP mock LDAP server with headers & IP auth
    if DEBUG:
        result = await loop.run_in_executor(
            None, _http_mock_ldap_search_sync, filterstr
        )
        LDAP_CACHE[filterstr] = result
        return result

    # Production mode: use standard python-ldap
    if LDAP is None and ldap is not None:
        LDAP = ldap.initialize(LDAP_HOST)

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

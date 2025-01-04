"""
MongoDB Initialization Module

This module sets up a connection to a MongoDB database.
This module connects to the MongoDB database using environment variables for authentication.

Environment Variables:
    `MONGO_USERNAME` (str): MongoDB username. Defaults to "username".
    `MONGO_PASSWORD` (str): MongoDB password. Defaults to "password".
    `MONGO_PORT` (str): MongoDB port. Defaults to "27017".
    `MONGO_DATABASE` (str): MongoDB database name. Defaults to "default".

"""

from os import getenv

from pymongo import MongoClient

# get mongodb URI and database name from environment variale
MONGO_URI = "mongodb://{}:{}@mongo:{}/".format(
    getenv("MONGO_USERNAME", default="username"),
    getenv("MONGO_PASSWORD", default="password"),
    getenv("MONGO_PORT", default="27107"),
)
MONGO_DATABASE = getenv("MONGO_DATABASE", default="default")

# instantiate mongo client
client = MongoClient(MONGO_URI)

# get database
db = client[MONGO_DATABASE]

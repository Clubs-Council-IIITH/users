"""
MongoDB Initialization Module.

This module sets up the connection to the MongoDB database.

Attributes:
    MONGO_USERNAME (str): An environment variable having MongoDB username. 
                          Defaults to "username".
    MONGO_PASSWORD (str): An environment variable having MongoDB password. 
                          Defaults to "password".
    MONGO_PORT (str): MongoDB port. Defaults to "27017".
    MONGO_URI (str): MongoDB URI.
    MONGO_DATABASE (str): MongoDB database name.
    client (MongoClient): MongoDB client.
    db (Database): Entire MongoDB database.
"""

from os import getenv

from pymongo import MongoClient

# get mongodb URI and database name from environment variable
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

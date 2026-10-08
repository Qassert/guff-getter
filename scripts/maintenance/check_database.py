import os
from newsmuncher.config import ENV_FILE
from pymongo.mongo_client import MongoClient # type: ignore
from pymongo.server_api import ServerApi # type: ignore
from dotenv import load_dotenv # type: ignore

# Load environment variables
load_dotenv(ENV_FILE)

# Get MongoDB URI from .env file
MONGO_URI = os.getenv("MONGO_URI")

# Create a new client and connect to the server
client = MongoClient(MONGO_URI, server_api=ServerApi('1'))

# Test connection
try:
    client.admin.command('ping')
    print("✅ Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print("❌ Connection failed:", e)

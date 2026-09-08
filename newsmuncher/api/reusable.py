from newsmuncher.config import ENV_FILE
from fastapi import FastAPI, HTTPException
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from bson import ObjectId
import os
import certifi
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List

# Load environment variables
load_dotenv(ENV_FILE)

# Connect to MongoDB
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI, server_api=ServerApi('1'), tlsCAFile=certifi.where())

# Define database & collection
db = client["funny_json_db"]
reusable_collection = db["reusable_entries"]

# Initialize FastAPI
app = FastAPI()

# Pydantic model for single and multiple entries
class ReusableEntry(BaseModel):
    title: str
    description: str
    extract: str

class ReusableEntryWithUsage(BaseModel):
    title: str
    description: str
    extract: str
    numberOftimesUsed: int

class ReusableEntries(BaseModel):
    entries: List[ReusableEntryWithUsage]

# ✅ POST - Add a Single Reusable Entry (numberOftimesUsed set to 0)
@app.post("/add/")
def add_reusable_entry(entry: ReusableEntry):
    new_entry = {
        "title": entry.title,
        "description": entry.description,
        "extract": entry.extract,
        "numberOftimesUsed": 0
    }
    inserted_id = reusable_collection.insert_one(new_entry).inserted_id
    return {"id": str(inserted_id), "message": "Reusable entry added successfully"}

# ✅ POST - Add Multiple Reusable Entries (clears collection before adding)
@app.post("/add_bulk/")
def add_reusable_entries(entries: ReusableEntries):
    reusable_collection.delete_many({})  # Clear existing entries
    new_entries = [
        {
            "title": entry.title,
            "description": entry.description,
            "extract": entry.extract,
            "numberOftimesUsed": entry.numberOftimesUsed
        }
        for entry in entries.entries
    ]
    result = reusable_collection.insert_many(new_entries)
    return {"inserted_ids": [str(_id) for _id in result.inserted_ids], "message": "Reusable entries added successfully after clearing existing data"}

# ✅ GET - Retrieve One Entry and Increment numberOftimesUsed
@app.get("/get_one/")
def get_one_reusable_entry():
    entry = reusable_collection.find_one_and_update(
        {},
        {'$inc': {"numberOftimesUsed": 1}},
        sort=[("numberOftimesUsed", 1)]  # Get the least used entry
    )
    if not entry:
        raise HTTPException(status_code=404, detail="No reusable entries found")
    entry["id"] = str(entry["_id"])
    del entry["_id"]
    return entry

# ✅ GET - Retrieve All Reusable Entries
@app.get("/get_all/")
def get_all_reusable_entries():
    entries = list(reusable_collection.find())
    for entry in entries:
        entry["id"] = str(entry["_id"])
        del entry["_id"]
    return entries

# ✅ PUT - Increment numberOftimesUsed for a specific entry
@app.put("/increment_usage/{id}")
def increment_usage(id: str):
    result = reusable_collection.update_one(
        {"_id": ObjectId(id)},
        {'$inc': {"numberOftimesUsed": 1}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Entry not found or failed to increment usage.")
    return {"message": "numberOftimesUsed incremented successfully"}

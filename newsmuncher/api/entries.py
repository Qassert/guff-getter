from newsmuncher.config import ENV_FILE
from fastapi import APIRouter, HTTPException, Request, Depends, Cookie
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from bson import ObjectId
import os
import certifi
from dotenv import load_dotenv  # type: ignore
from pydantic import BaseModel, field_validator  # type: ignore
import datetime

# Load environment variables
load_dotenv(ENV_FILE)

# Connect to MongoDB
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI, server_api=ServerApi('1'), tlsCAFile=certifi.where())
db = client["funny_json_db"]
collection = db["entries"]

router = APIRouter()

class ImageMetadata(BaseModel):
    image_url: str | None = None
    image_prompt: str | None = None
    image_model: str | None = None
    image_provider: str | None = None
    image_generated_at: str | None = None

    @field_validator('image_url')
    @classmethod
    def reference_only(cls, value):
        if value is not None and not (value.startswith(('https://', 'http://')) or
                                      (value.startswith('/') and not value.startswith('//'))):
            raise ValueError('Image must be an HTTP URL or local path, never embedded image data.')
        return value


class Post(ImageMetadata):
    title: str
    description: str
    extract: str
    crazyReplacement1Title: str | None = None
    crazyReplacement1Extract: str | None = None
    crazyReplacement1done: bool = False
    creationUser: str | None = None
    rewrite_id: str | None = None
    image_owner: str | None = None



def get_active_pet(active_pet: str = Cookie(None)):
    if not active_pet:
        raise HTTPException(status_code=401, detail="You must use a pet first.")
    return active_pet

@router.post("/create/")
def create_entry(post: Post, request: Request):
    creation_date = datetime.datetime.utcnow()
    creation_user = request.cookies.get("active_pet")

    if not creation_user:
        raise HTTPException(status_code=401, detail="User not authenticated")

    new_entry = {
        "title": post.title,
        "description": post.description,
        "extract": post.extract,
        "crazyReplacement1Title": post.crazyReplacement1Title,
        "crazyReplacement1Extract": post.crazyReplacement1Extract,
        "crazyReplacement1done": post.crazyReplacement1done,
        "flagForDeleteCount": 0,
        "flagForFunnyCount": 0,
        "chatHistory": [],
        "creationDate": datetime.datetime.utcnow(),
        "creationUser": post.creationUser or request.cookies.get("active_pet")
    }

    if post.rewrite_id:
        new_entry.update(rewrite_id=post.rewrite_id, image_owner=creation_user)
        new_entry.update({key: getattr(post, key) for key in ImageMetadata.model_fields
                          if getattr(post, key) is not None})
    inserted_id = collection.insert_one(new_entry).inserted_id

    return {
        "id": str(inserted_id),
        "message": "Post created successfully",
        "creationDate": creation_date,
        "creationUser": creation_user
    }


@router.get("/entries/")
def get_entries():
    posts = list(collection.find({}, {
        "_id": 1,
        "title": 1,
        "description": 1,
        "extract": 1,
        "crazyReplacement1done": 1,
        "crazyReplacement1Title": 1,
        "crazyReplacement1Extract": 1,
        "flagForDeleteCount": 1,
        "flagForFunnyCount": 1,
        "chatHistory": 1,
        "creationDate": 1,
        "creationUser": 1,
        **{key: 1 for key in ImageMetadata.model_fields},
        "rewrite_id": 1
    }).sort("creationDate", -1))

    return [
        {
            "id": str(post["_id"]),
            "title": post["title"],
            "description": post.get("description", ""),
            "extract": post["extract"],
            "crazyReplacement1done": post.get("crazyReplacement1done", False),
            "crazyReplacement1Title": post.get("crazyReplacement1Title"),
            "crazyReplacement1Extract": post.get("crazyReplacement1Extract"),
            "flagForDeleteCount": post.get("flagForDeleteCount", 0),
            "flagForFunnyCount": post.get("flagForFunnyCount", 0),
            "chatHistory": post.get("chatHistory", []),
            "creationDate": post.get("creationDate"),
            "creationUser": post.get("creationUser"),
            **{key: post[key] for key in (*ImageMetadata.model_fields, "rewrite_id") if key in post}
        }
        for post in posts
    ]

@router.get("/entry/{id}")
def get_entry(id: str):
    post = collection.find_one({"_id": ObjectId(id)})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    post["_id"] = str(post["_id"])
    return post

@router.put("/entry/{id}")
def update_crazy_fields(
    id: str,
    crazyReplacement1Title: str = None,
    crazyReplacement1Extract: str = None,
    request: Request = None
):
    update_fields = {}
    if crazyReplacement1Title:
        update_fields["crazyReplacement1Title"] = crazyReplacement1Title
        update_fields["crazyReplacement1Extract"] = crazyReplacement1Extract
        update_fields["crazyReplacement1done"] = True
        update_fields["creationDate"] = datetime.datetime.utcnow()

    # Extract the creationUser from the cookie
    creation_user = request.cookies.get("active_pet")
    if creation_user:
        # Only set creationUser if it doesn't already exist
        existing_entry = collection.find_one({"_id": ObjectId(id)})
        if existing_entry and not existing_entry.get("creationUser"):
            update_fields["creationUser"] = creation_user

    result = collection.update_one({"_id": ObjectId(id)}, {"$set": update_fields})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Post not found or nothing to update")
    return {"message": "Post updated successfully", "creationDate": update_fields.get("creationDate")}


@router.delete("/entry/{id}")
def delete_entry(id: str):
    result = collection.delete_one({"_id": ObjectId(id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Post not found")
    return {"message": "Post deleted successfully"}

@router.delete("/entries/all_for_user")
def delete_all_entries_for_user(current_user: str = Depends(get_active_pet)):
    result = collection.delete_many({
        "creationUser": current_user,
        "crazyReplacement1done": False
    })
    return {
        "message": f"{result.deleted_count} unprocessed entries deleted for user {current_user}"
    }

@router.delete("/entries/all")
def delete_all_entries():
    result = collection.delete_many({})
    return {"message": f"All entries deleted. Total: {result.deleted_count}"}

class ImageUpdate(ImageMetadata):
    rewrite_id: str


@router.patch('/entry/{id}/image')
def update_entry_image(id: str, payload: ImageUpdate, active_pet: str = Cookie(None)):
    if not active_pet:
        raise HTTPException(status_code=401, detail='No active pet selected.')
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail='Invalid entry ID.')
    metadata = payload.model_dump(exclude_none=True, exclude={'rewrite_id'})
    if metadata.get('image_url', '').startswith('data:'):
        raise HTTPException(status_code=400, detail='Image must be a URL/reference.')
    result = collection.update_one(
        {'_id': ObjectId(id), 'rewrite_id': payload.rewrite_id, 'image_owner': active_pet},
        {'$set': metadata})
    if not result.matched_count:
        raise HTTPException(status_code=404, detail='Matching rewrite not found.')
    return {'message': 'Image associated with rewrite.'}

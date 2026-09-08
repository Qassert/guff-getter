from newsmuncher.config import AVATARS_DIR, TEMPLATES_DIR
from fastapi import APIRouter, HTTPException, Request, Form, UploadFile, File, Response
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from passlib.context import CryptContext
import os
import uuid
import re
from pymongo.errors import DuplicateKeyError
from typing import List

# Environment setup
MONGO_URI = os.getenv("MONGO_URI")
UPLOAD_FOLDER = AVATARS_DIR
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# DB setup
client = AsyncIOMotorClient(MONGO_URI)
db = client["pet_adoption_db"]
pets_collection = db["pets"]

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# Router and templates
router = APIRouter()
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Routes

@router.get("/get_all_pets")
async def get_all_pets():
    pets = await pets_collection.find().to_list(None)
    return [{
        "avatar": pet["avatar"],
        "name": pet.get("name"),
        "adopted": pet.get("adopted", False)
    } for pet in pets]

@router.get("/view_pets")
async def view_pets(request: Request):
    pets = await pets_collection.find().to_list(None)
    return templates.TemplateResponse(
        request=request,
        name="view_pets.html",
        context={"request": request, "pets": pets},
    )

@router.get("/pets/select/{avatar}", response_class=HTMLResponse)
@router.get("/select/{avatar}", response_class=HTMLResponse)
async def select_pet(request: Request, avatar: str):
    pet = await pets_collection.find_one({"avatar": avatar})
    if not pet:
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={"request": request, "message": "Pet not found."},
        )
    template = "login_pet.html" if pet.get("name") else "adopt_pet.html"
    return templates.TemplateResponse(
        request=request,
        name=template,
        context={"request": request, "pet": pet},
    )

@router.post("/adopt_pet/{avatar}")
async def adopt_pet(
    request: Request,
    avatar: str,
    name: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...)
):
    if password != confirm_password:
        return templates.TemplateResponse(
            request=request,
            name="adopt_pet.html",
            context={
                "request": request,
                "pet": {"avatar": avatar},
                "error": "Passwords do not match. Try again!"
            },
        )

    existing_pet = await pets_collection.find_one({"avatar": avatar})
    if not existing_pet:
        raise HTTPException(status_code=404, detail="Pet not found.")
    if existing_pet.get("adopted", False):
        return templates.TemplateResponse(
            request=request,
            name="adopt_pet.html",
            context={
                "request": request,
                "pet": existing_pet,
                "error": "This pet is already adopted!"
            },
        )

    capitalized_name = name.strip().capitalize()
    if not capitalized_name:
        return templates.TemplateResponse(
            request=request,
            name="adopt_pet.html",
            context={
                "request": request, "pet": existing_pet,
                "error": "Please enter a pet name."
            },
        )

    # Check legacy names too, without renaming existing pets.
    duplicate = await pets_collection.find_one({
        "name": {"$regex": r"^\s*" + re.escape(capitalized_name) + r"\s*$", "$options": "i"}
    })
    if duplicate:
        return templates.TemplateResponse(
            request=request,
            name="adopt_pet.html",
            context={
                "request": request, "pet": existing_pet,
                "error": "That name is already taken. Please choose another."
            },
        )

    # Only new adoptions have this key, so old duplicates remain intact.
    # The unique index also rejects simultaneous claims for the same name.
    await pets_collection.create_index(
        "name_key", unique=True,
        partialFilterExpression={"name_key": {"$type": "string"}},
        name="unique_pet_name_key"
    )
    hashed_password = get_password_hash(password)

    try:
        result = await pets_collection.update_one(
            {"avatar": avatar, "adopted": {"$ne": True}},
            {"$set": {
                "name": capitalized_name,
                "name_key": capitalized_name.casefold(),
                "password": hashed_password,
                "adopted": True,
                "last_used": datetime.utcnow()
            }}
        )
    except DuplicateKeyError:
        return templates.TemplateResponse(
            request=request,
            name="adopt_pet.html",
            context={
                "request": request, "pet": existing_pet,
                "error": "That name is already taken. Please choose another."
            },
        )
    if result.matched_count != 1:
        return templates.TemplateResponse(
            request=request,
            name="adopt_pet.html",
            context={
                "request": request, "pet": existing_pet,
                "error": "This pet is already adopted!"
            },
        )

    response = RedirectResponse(url=f"/pets/pet_profile/{avatar}", status_code=303)
    response.set_cookie(key="active_pet", value=avatar, httponly=True, max_age=86400)
    return response

@router.post("/use_pet/{avatar}")
async def use_pet(
    request: Request,
    avatar: str,
    password: str = Form(...),
):
    pet = await pets_collection.find_one({"avatar": avatar})
    if not pet or not pet.get("adopted"):
        return templates.TemplateResponse(
            request=request,
            name="login_pet.html",
            context={
                "request": request,
                "pet": {"avatar": avatar, "name": pet.get("name") if pet else None},
                "error": "Pet not found or not adopted."
            },
        )
    if not verify_password(password, pet["password"]):
        return templates.TemplateResponse(
            request=request,
            name="login_pet.html",
            context={
                "request": request,
                "pet": pet,
                "error": "Incorrect password. Try again!"
            },
        )

    await pets_collection.update_one(
        {"avatar": avatar},
        {"$set": {"last_used": datetime.utcnow()}}
    )

    response = RedirectResponse(url=f"/pets/pet_profile/{avatar}", status_code=303)
    response.set_cookie(key="active_pet", value=avatar, httponly=True, max_age=86400)
    return response

@router.get("/pet_profile/{avatar}", response_class=HTMLResponse)
async def pet_profile(request: Request, avatar: str):
    pet = await pets_collection.find_one({"avatar": avatar})
    if not pet:
        raise HTTPException(status_code=404, detail="Pet not found.")
    return templates.TemplateResponse(
        request=request,
        name="pet_profile.html",
        context={"request": request, "pet": pet},
    )

@router.post("/upload_pets")
async def upload_pets(images: List[UploadFile] = File(...)):
    uploaded_files = []
    for image in images:
        if image.content_type != "image/jpeg":
            raise HTTPException(status_code=400, detail=f"{image.filename} is not a valid JPG file.")
        image_data = await image.read()
        if len(image_data) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail=f"{image.filename} exceeds 2MB limit.")

        filename = f"{uuid.uuid4().hex}.jpg"
        with open(os.path.join(UPLOAD_FOLDER, filename), "wb") as f:
            f.write(image_data)

        await pets_collection.insert_one({"avatar": filename, "adopted": False})
        uploaded_files.append(filename)

    return {"message": "Pets uploaded successfully.", "avatars": uploaded_files}

@router.post("/unadopt_pet/{avatar}")
async def unadopt_pet(avatar: str):
    pet = await pets_collection.find_one({"avatar": avatar})
    if not pet:
        raise HTTPException(status_code=404, detail="Pet not found.")
    if not pet.get("adopted"):
        raise HTTPException(status_code=400, detail="Pet is not adopted.")

    await pets_collection.update_one(
        {"avatar": avatar},
        {"$set": {
            "adopted": False,
            "name": None,
            "password": None,
            "last_used": None
        }, "$unset": {"name_key": ""}}
    )
    return {"message": f"Pet '{avatar}' has been unadopted successfully."}

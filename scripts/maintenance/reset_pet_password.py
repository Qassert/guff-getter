"""Local administrator recovery; never exposed as a web endpoint."""

import argparse
from getpass import getpass
from newsmuncher.config import ENV_FILE

import certifi
from dotenv import dotenv_values
from passlib.context import CryptContext
from pymongo import MongoClient
from pymongo.errors import PyMongoError


def main():
    parser = argparse.ArgumentParser(description="Reset an adopted pet's password locally.")
    parser.add_argument("name", help="Exact pet name, for example Andy")
    parser.add_argument("--avatar", help="Avatar filename from the pet's login page URL")
    args = parser.parse_args()
    settings = dotenv_values(ENV_FILE)
    uri = settings.get("MONGO_URI")
    if not uri:
        print("Local MongoDB settings are missing. No changes made.")
        return 1

    try:
        with MongoClient(uri, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=10000) as client:
            pets = client["pet_adoption_db"]["pets"]
            query = {"name": args.name, "adopted": True}
            if args.avatar:
                query["avatar"] = args.avatar
            matches = list(pets.find(
                query,
                {"_id": 1, "password": 1},
            ).limit(2))
            if len(matches) != 1:
                print("Expected exactly one adopted pet. If names repeat, use --avatar with the filename from the login page URL. No changes made.")
                return 1

            password = getpass("New password (hidden): ")
            confirmation = getpass("Repeat new password (hidden): ")
            if password != confirmation:
                print("Passwords do not match. No changes made.")
                return 1
            if not password or len(password.encode("utf-8")) > 72:
                print("Use a nonempty password of at most 72 UTF-8 bytes. No changes made.")
                return 1

            hashed = CryptContext(schemes=["bcrypt"], deprecated="auto").hash(password)
            pet = matches[0]
            result = pets.update_one(
                {"_id": pet["_id"], "password": pet.get("password"), "adopted": True},
                {"$set": {"password": hashed}},
            )
            if result.matched_count != 1:
                print("The pet changed during recovery. No password was updated; try again.")
                return 1
            print("Password updated. The pet and saved posts are preserved.")
            return 0
    except PyMongoError:
        print("Database recovery failed. Check Atlas connectivity before retrying.")
        return 1
    except (EOFError, KeyboardInterrupt):
        print("\nRecovery cancelled.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

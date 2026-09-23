"""Server-validated gallery sessions issued only after successful pet login."""
from datetime import datetime, timedelta, timezone
import hashlib
import secrets

from fastapi import HTTPException

COOKIE = 'gallery_session'


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


async def issue_session(collection, response, request, pet):
    token = secrets.token_urlsafe(32)
    await collection.create_index('expires_at', expireAfterSeconds=0)
    await collection.insert_one({'_id': digest(token), 'pet': pet['avatar'],
        'password_version': digest(pet['password']),
        'expires_at': datetime.now(timezone.utc) + timedelta(hours=24)})
    response.set_cookie(COOKIE, token, httponly=True, secure=request.url.scheme == 'https',
                        samesite='strict', max_age=86400, path='/')


async def authenticate(collection, pets, token):
    if not token or len(token) > 100:
        raise HTTPException(401, 'Sign in to your pet again to open the Promotion Gallery.')
    session = await collection.find_one({'_id': digest(token),
        'expires_at': {'$gt': datetime.now(timezone.utc)}})
    pet = await pets.find_one({'avatar': session['pet'], 'adopted': True}) if session else None
    if not pet or not pet.get('password') or digest(pet['password']) != session['password_version']:
        raise HTTPException(401, 'Sign in to your pet again to open the Promotion Gallery.')
    return {'id': session['_id'], 'pet': pet['avatar']}

"""Moderation data boundary only. No public route or authorization is supplied here."""
from typing import Literal

GalleryStatus = Literal['pending', 'approved', 'rejected']


def nomination_state(post):
    """Conservative read-time compatibility; never auto-approve legacy content."""
    return dict(nominated=post.get('nominated', bool(post.get('crazyReplacement1done'))),
                gallery_status=post.get('gallery_status', 'pending'))


def moderation_fields(status: GalleryStatus):
    """Future authenticated moderation service can use this validated update."""
    if status not in ('pending', 'approved', 'rejected'):
        raise ValueError('Invalid gallery status')
    return {'gallery_status': status}


APPROVED_GALLERY_FILTER = {'nominated': True, 'gallery_status': 'approved'}

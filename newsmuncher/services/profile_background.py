"""Select a permanent local illustration without reading image binaries."""
import random
from uuid import UUID

from newsmuncher.config import GENERATED_IMAGES_DIR


def random_nominated_background(collection, directory=GENERATED_IMAGES_DIR):
    # Reservoir sampling stays uniform across available images using constant memory.
    # Projection avoids loading article text or image data.
    candidates = collection.find(
        {"nominated": True, "image_url": {"$regex": r"^/generated-images/"}},
        {"_id": 0, "image_url": 1, "rewrite_id": 1},
    )
    selected = None
    available = 0
    for entry in candidates:
        url = entry.get("image_url", "")
        try:
            filename = url.removeprefix("/generated-images/")
            image_id = UUID(filename.removesuffix(".png"))
            if url != f"/generated-images/{image_id}.png":
                continue
            path = directory / filename
            if path.is_symlink() or not path.is_file() or path.stat().st_size == 0:
                continue
        except (ValueError, OSError, AttributeError):
            continue
        available += 1
        if random.randrange(available) == 0:
            selected = {"image_url": url, "rewrite_id": str(image_id)}
    return selected

"""Select a permanent local illustration without reading image binaries."""
import random
from uuid import UUID

from pathlib import Path

from newsmuncher.config import GENERATED_IMAGES_READ_DIRS


def random_nominated_background(collection, directory=GENERATED_IMAGES_READ_DIRS):
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
            directories = ((Path(directory),) if isinstance(directory, (str, Path))
                           else tuple(map(Path, directory)))
            paths = (root / filename for root in directories)
            if not any(not path.is_symlink() and path.is_file() and path.stat().st_size > 0
                       for path in paths):
                continue
        except (ValueError, OSError, AttributeError):
            continue
        available += 1
        if random.randrange(available) == 0:
            selected = {"image_url": url, "rewrite_id": str(image_id)}
    return selected

"""Static media serving with local-write and read-only fallback directories."""

from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException


class FallbackStaticFiles(StaticFiles):
    def __init__(self, directories, **kwargs):
        directories = tuple(directories)
        super().__init__(directory=directories[0], **kwargs)
        self.fallbacks = tuple(
            StaticFiles(directory=directory, **kwargs) for directory in directories[1:]
        )

    async def get_response(self, path, scope):
        try:
            response = await super().get_response(path, scope)
        except HTTPException as exc:
            if exc.status_code != 404:
                raise
            response = None
        if response is not None and response.status_code != 404:
            return response
        for fallback in self.fallbacks:
            try:
                candidate = await fallback.get_response(path, scope)
            except HTTPException as exc:
                if exc.status_code == 404:
                    continue
                raise
            if candidate.status_code != 404:
                return candidate
        return response or await super().get_response(path, scope)

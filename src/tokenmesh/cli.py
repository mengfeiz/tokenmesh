"""Tokenmesh CLI."""
import uvicorn
from .config import get_settings


def main():
    settings = get_settings()
    uvicorn.run(
        "tokenmesh.app:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=False,
    )


if __name__ == "__main__":
    main()

from __future__ import annotations

import uvicorn

from cogn_os.api.app import create_app
from cogn_os.config import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(create_app(settings), host=settings.api_host, port=settings.api_port)


if __name__ == "__main__":
    main()

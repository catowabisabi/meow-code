#!/usr/bin/env python3
import uvicorn
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from api_server.config import Settings


if __name__ == "__main__":
    settings = Settings()
    uvicorn.run(
        "api_server.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info",
        access_log=True,
    )

"""Start: python -m orchestrator.channels.web  (-> http://HOST:PORT)."""
import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run("orchestrator.channels.web.app:app",
                host=os.environ.get("LUNA_OS_HOST", "127.0.0.1"),
                port=int(os.environ.get("LUNA_OS_PORT", "8765")),
                log_level="info")

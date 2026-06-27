"""Start: python -m orchestrator.channels.web  (-> http://HOST:PORT)."""
import os

import uvicorn

if __name__ == "__main__":
    # PORT (vom Preview-Harness gesetzt) hat Vorrang vor LUNA_OS_PORT; sonst Default 8765.
    port = int(os.environ.get("PORT") or os.environ.get("LUNA_OS_PORT") or "8765")
    uvicorn.run("orchestrator.channels.web.app:app",
                host=os.environ.get("LUNA_OS_HOST", "127.0.0.1"),
                port=port,
                log_level="info")

"""Desktop entry point - starts the FastAPI server with auto-open browser."""

import os
import sys
import webbrowser
import threading
from pathlib import Path

import uvicorn


def get_data_dir() -> Path:
    """Get a persistent data directory for the running user."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    elif sys.platform == "darwin":
        base = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME", os.path.join(os.path.expanduser("~"), ".local", "share"))
    data_dir = Path(base) / "IchibanKuji"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def open_browser(url: str):
    threading.Timer(2.0, lambda: webbrowser.open(url)).start()


def main():
    port = int(os.environ.get("PORT", "8000"))
    host = os.environ.get("HOST", "127.0.0.1")

    data_dir = get_data_dir()
    os.environ["ICHIBAN_DATA_DIR"] = str(data_dir)
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{data_dir}/ichiban.db"

    url = f"http://{host}:{port}"
    print(f"=== Ichiban Kuji Server ===")
    print(f"URL:     {url}")
    print(f"Data:    {data_dir}")
    print(f"===========================")
    open_browser(url)

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()

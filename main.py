import os

import uvicorn


def main() -> None:
    """Run the local Confluence preview server."""
    uvicorn.run(
        "parse_confluence:app",
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8000")),
    )


if __name__ == "__main__":
    main()

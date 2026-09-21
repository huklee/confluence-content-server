"""Backward-compatible entry point for the packaged server application."""

from confluence_content_server.app import (
    app,
    create_parser,
    editor,
    main,
    render,
    samples,
)

__all__ = ["app", "create_parser", "editor", "main", "render", "samples"]


if __name__ == "__main__":
    main()

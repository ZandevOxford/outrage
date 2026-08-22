"""Allow ``python -m outrage`` as an alternative to the outrage-server script."""

from .server import main

if __name__ == "__main__":
    main()

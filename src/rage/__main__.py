"""Allow ``python -m rage`` as an alternative to the rage-server script."""

from .server import main

if __name__ == "__main__":
    main()

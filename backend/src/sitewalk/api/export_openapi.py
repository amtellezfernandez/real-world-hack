import json
import sys

from sitewalk.api.main import app


def main() -> None:
    """Write the generated OpenAPI contract to stdout."""
    json.dump(app.openapi(), sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()

import json
import sys

from sitewalk.config import build_provider_env, get_settings
from sitewalk.review_export.encord_config import build_encord_config_from_env
from sitewalk.review_export.encord_live import create_robot_safety_ontology
from sitewalk.review_export.encord_ontology import build_robot_safety_ontology_spec


def print_ontology_main() -> None:
    """Print the Encord ontology JSON expected by the app."""
    json.dump(
        build_robot_safety_ontology_spec().model_dump(mode="json"),
        sys.stdout,
        indent=2,
    )
    sys.stdout.write("\n")


def create_ontology_main() -> None:
    """Create the Encord ontology from configured credentials."""
    settings = get_settings()
    config = build_encord_config_from_env(env=build_provider_env(settings))
    result = create_robot_safety_ontology(config=config)
    json.dump(result.model_dump(mode="json"), sys.stdout, indent=2)
    sys.stdout.write("\n")

    if result.status != "created":
        raise SystemExit(1)

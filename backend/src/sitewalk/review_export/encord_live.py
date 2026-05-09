from collections.abc import Iterable
from pathlib import Path
from importlib import import_module
from typing import Literal, Protocol

from pydantic import Field

from sitewalk.contracts import ContractModel, ExportStatus
from sitewalk.review_export.encord_config import (
    EncordConfig,
    is_encord_configured,
    is_encord_dataset_configured,
)
from sitewalk.review_export.encord_ontology import (
    EncordOntologySpec,
    build_robot_safety_ontology_spec,
)
from sitewalk.review_export.incident_packet import EncordIncidentExportPacket


class EncordIntegrationUnavailable(RuntimeError):
    """Raised when a live Encord operation cannot run."""


class EncordCreatedOntology(Protocol):
    """Small protocol for the Encord ontology response."""

    ontology_hash: str


class EncordUploadedItem(Protocol):
    """Small protocol for uploaded Encord data items."""

    uuid: object


class EncordStorageFolder(Protocol):
    """Small protocol for the Encord storage folder SDK object."""

    name: str

    def upload_image(
        self,
        file_path: str,
        *,
        title: str,
        client_metadata: dict[str, str],
    ) -> EncordUploadedItem: ...


class EncordDataset(Protocol):
    """Small protocol for the Encord dataset SDK object."""

    def link_items(self, item_uuids: list[str]) -> object: ...


class EncordClient(Protocol):
    """Small protocol for the Encord client operations this module uses."""

    def create_ontology(
        self,
        title: str,
        *,
        description: str,
        structure: object,
    ) -> EncordCreatedOntology: ...

    def list_storage_folders(self) -> Iterable[EncordStorageFolder]: ...

    def create_storage_folder(self, name: str) -> EncordStorageFolder: ...

    def get_dataset(self, dataset_id: str) -> EncordDataset: ...


class EncordOntologyCreationResult(ContractModel):
    """Result of attempting to create the Encord ontology."""

    status: Literal["created", "unavailable", "failed"]
    ontology_title: str
    ontology_hash: str | None = None
    detail: str


class EncordIncidentExportResult(ContractModel):
    """Result of attempting to upload incident evidence to Encord."""

    status: ExportStatus
    detail: str
    provider_sample_ids: list[str] = Field(default_factory=list)
    packet: EncordIncidentExportPacket


def create_robot_safety_ontology(
    *,
    config: EncordConfig,
    ontology: EncordOntologySpec | None = None,
) -> EncordOntologyCreationResult:
    """Create the Encord ontology used for incident review."""
    ontology_spec = ontology or build_robot_safety_ontology_spec()

    if not is_encord_configured(config=config):
        return EncordOntologyCreationResult(
            status="unavailable",
            ontology_title=ontology_spec.title,
            detail=(
                "Set ENCORD_SSH_KEY_FILE and ENCORD_PROJECT_ID before creating "
                "the live Encord ontology."
            ),
        )

    try:
        client = build_encord_client(config=config)
        ontology_structure = build_encord_sdk_ontology_structure(ontology_spec)
        created_ontology = client.create_ontology(
            ontology_spec.title,
            description=ontology_spec.description,
            structure=ontology_structure,
        )
    except Exception as exc:  # pragma: no cover - exercised only with live SDK.
        return EncordOntologyCreationResult(
            status="failed",
            ontology_title=ontology_spec.title,
            detail=f"Encord ontology creation failed: {exc}",
        )

    return EncordOntologyCreationResult(
        status="created",
        ontology_title=ontology_spec.title,
        ontology_hash=getattr(created_ontology, "ontology_hash", None),
        detail="Created Encord ontology for robot safety incidents.",
    )


def export_incident_packet_to_encord(
    *,
    config: EncordConfig,
    packet: EncordIncidentExportPacket,
    before_image_path: Path | None = None,
    after_image_path: Path | None = None,
) -> EncordIncidentExportResult:
    """Upload incident images and metadata to Encord when configured."""
    if not is_encord_dataset_configured(config=config):
        missing_parts = [
            name
            for name, value in (
                ("ENCORD_SSH_KEY_FILE", config.ssh_key_file),
                ("ENCORD_PROJECT_ID", config.project_id),
                ("ENCORD_DATASET_ID", config.dataset_id),
            )
            if value is None
        ]
        return EncordIncidentExportResult(
            status=ExportStatus.EXPORT_UNAVAILABLE,
            detail=(
                "Set "
                f"{', '.join(missing_parts)} "
                "to upload incident evidence to Encord."
            ),
            packet=packet,
        )

    image_paths = [
        path for path in (before_image_path, after_image_path) if path is not None
    ]
    missing_paths = [path for path in image_paths if not path.exists()]
    if len(image_paths) < 2 or len(missing_paths) > 0:
        return EncordIncidentExportResult(
            status=ExportStatus.EXPORT_UNAVAILABLE,
            detail=(
                "Live Encord upload needs concrete before_image_path and "
                "after_image_path files. The packet remains ready for local review."
            ),
            packet=packet,
        )

    try:
        if config.dataset_id is None:
            raise EncordIntegrationUnavailable("ENCORD_DATASET_ID is not configured.")

        client = build_encord_client(config=config)
        storage_folder = get_or_create_storage_folder(
            client=client,
            folder_name=config.storage_folder,
        )
        uploaded_item_ids = [
            upload_incident_image(
                storage_folder=storage_folder,
                image_path=image_path,
                packet=packet,
                role=role,
            )
            for image_path, role in zip(image_paths, ("before", "after"), strict=True)
        ]
        dataset = client.get_dataset(config.dataset_id)
        dataset.link_items(uploaded_item_ids)
    except Exception as exc:  # pragma: no cover - exercised only with live SDK.
        return EncordIncidentExportResult(
            status=ExportStatus.EXPORT_UNAVAILABLE,
            detail=f"Encord incident upload failed: {exc}",
            packet=packet,
        )

    return EncordIncidentExportResult(
        status=ExportStatus.EXPORTED,
        detail="Uploaded incident before/after evidence to Encord.",
        provider_sample_ids=[str(item_id) for item_id in uploaded_item_ids],
        packet=packet,
    )


def build_encord_client(*, config: EncordConfig) -> EncordClient:
    """Build an Encord SDK client from the SSH private key credential."""
    try:
        encord_module = import_module("encord")
    except ImportError as exc:  # pragma: no cover - depends on optional SDK.
        raise EncordIntegrationUnavailable(
            "Install the optional encord package before live Encord operations."
        ) from exc

    if config.ssh_key_file is None:
        raise EncordIntegrationUnavailable("ENCORD_SSH_KEY_FILE is not configured.")

    encord_user_client = getattr(encord_module, "EncordUserClient")

    return encord_user_client.create_with_ssh_private_key(
        ssh_private_key_path=config.ssh_key_file,
        domain=config.domain,
    )


def build_encord_sdk_ontology_structure(ontology: EncordOntologySpec) -> object:
    """Translate the local ontology spec into Encord SDK objects."""
    try:
        encord_objects = import_module("encord.objects")
        encord_attributes = import_module("encord.objects.attributes")
    except ImportError as exc:  # pragma: no cover - depends on optional SDK.
        raise EncordIntegrationUnavailable(
            "Install the optional encord package before live Encord operations."
        ) from exc

    shape_by_name = {
        "bounding_box": getattr(encord_objects.Shape, "BOUNDING_BOX"),
        "polygon": getattr(encord_objects.Shape, "POLYGON"),
    }
    structure = getattr(encord_objects, "OntologyStructure")()
    radio_attribute = getattr(encord_attributes, "RadioAttribute")
    text_attribute = getattr(encord_attributes, "TextAttribute")

    for ontology_object in ontology.objects:
        structure.add_object(
            name=ontology_object.name,
            shape=shape_by_name[ontology_object.shape],
        )

    for classification in ontology.classifications:
        sdk_classification = structure.add_classification()
        if classification.kind == "radio":
            sdk_attribute = sdk_classification.add_attribute(
                radio_attribute,
                classification.name,
            )
            for option in classification.options:
                sdk_attribute.add_option(option)
            continue

        sdk_classification.add_attribute(text_attribute, classification.name)

    return structure


def get_or_create_storage_folder(
    *,
    client: EncordClient,
    folder_name: str,
) -> EncordStorageFolder:
    """Return an Encord storage folder, creating it if absent."""
    for folder in client.list_storage_folders():
        if getattr(folder, "name", None) == folder_name:
            return folder

    return client.create_storage_folder(folder_name)


def upload_incident_image(
    *,
    storage_folder: EncordStorageFolder,
    image_path: Path,
    packet: EncordIncidentExportPacket,
    role: str,
) -> str:
    """Upload a single incident image with searchable incident metadata."""
    metadata = {
        "incident_id": packet.incident.id,
        "frame_role": role,
        "zone_id": packet.incident.zone_id,
        "review_decision": packet.review_sample.human_decision.value,
        "openai_outcome_summary": (
            packet.outcome_report.summary if packet.outcome_report is not None else ""
        ),
    }
    uploaded_item = storage_folder.upload_image(
        str(image_path),
        title=f"{packet.incident.id}-{role}{image_path.suffix}",
        client_metadata=metadata,
    )
    uploaded_uuid = getattr(uploaded_item, "uuid", uploaded_item)

    return str(uploaded_uuid)

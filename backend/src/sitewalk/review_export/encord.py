from collections.abc import Awaitable, Callable

from pydantic import Field

from sitewalk.contracts import (
    ContractModel,
    ExportStatus,
    ReviewDecision,
    ReviewSample,
)
from sitewalk.providers.ports import ReviewExporter
from sitewalk.review_export.encord_config import normalize_encord_project_id


class EncordReviewExportRequest(ContractModel):
    """Review sample export request for the Encord adapter boundary."""

    project_id: str = Field(min_length=1)
    incident_id: str
    before_frame_id: str
    after_frame_id: str
    labels: list[str]
    human_decision: ReviewDecision


class EncordReviewExportResult(ContractModel):
    """Provider response returned after an Encord sample export."""

    provider_sample_id: str = Field(min_length=1)


type EncordReviewExportClient = Callable[
    [EncordReviewExportRequest],
    Awaitable[EncordReviewExportResult],
]


def build_encord_review_exporter(
    *,
    client: EncordReviewExportClient,
    project_id: str | None,
) -> ReviewExporter:
    """Build an Encord exporter behind the review export port."""
    normalized_project_id = normalize_encord_project_id(project_id)

    async def export(review_sample: ReviewSample) -> ReviewSample:
        if normalized_project_id is None:
            return _copy_review_sample_with_status(
                review_sample=review_sample,
                export_status=ExportStatus.EXPORT_UNAVAILABLE,
            )

        await client(
            EncordReviewExportRequest(
                project_id=normalized_project_id,
                incident_id=review_sample.incident_id,
                before_frame_id=review_sample.before_frame_id,
                after_frame_id=review_sample.after_frame_id,
                labels=review_sample.labels,
                human_decision=review_sample.human_decision,
            ),
        )

        return _copy_review_sample_with_status(
            review_sample=review_sample,
            export_status=ExportStatus.EXPORTED,
        )

    return export


def _copy_review_sample_with_status(
    *,
    review_sample: ReviewSample,
    export_status: ExportStatus,
) -> ReviewSample:
    return review_sample.model_copy(update={"export_status": export_status})

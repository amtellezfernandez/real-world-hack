import pytest

from sitewalk.contracts import (
    ExportStatus,
    ProviderAvailability,
    ReviewDecision,
    ReviewExportProvider,
    ReviewSample,
)
from sitewalk.review_export.encord import (
    EncordReviewExportRequest,
    EncordReviewExportResult,
    build_encord_review_exporter,
)
from sitewalk.review_export.provider_status import (
    build_review_export_provider_statuses,
)

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def make_review_sample() -> ReviewSample:
    return ReviewSample(
        incident_id="incident-zone-workcell-a2-frame-workcell-sustained-blocked",
        before_frame_id="frame-workcell-sustained-blocked",
        after_frame_id="frame-workcell-after-clear",
        labels=["blocked_robot_workcell", "verified_clear"],
        human_decision=ReviewDecision.PENDING,
        export_status=ExportStatus.LOCAL_ONLY,
    )


def test_review_export_statuses_mark_missing_encord_credentials_unavailable() -> None:
    statuses = build_review_export_provider_statuses(env={})
    statuses_by_provider = {status.provider: status for status in statuses}

    assert statuses_by_provider[ReviewExportProvider.LOCAL_REVIEW].availability == (
        ProviderAvailability.AVAILABLE
    )
    assert statuses_by_provider[ReviewExportProvider.ENCORD].availability == (
        ProviderAvailability.UNCONFIGURED
    )
    assert "Encord export unavailable" in (
        statuses_by_provider[ReviewExportProvider.ENCORD].detail
    )
    assert "local review queue remains available" in (
        statuses_by_provider[ReviewExportProvider.ENCORD].detail
    )


def test_review_export_statuses_mark_configured_encord_as_scaffolded() -> None:
    statuses = build_review_export_provider_statuses(
        env={
            "ENCORD_API_KEY": "encord-key",
            "ENCORD_PROJECT_ID": "encord-project",
        },
    )
    statuses_by_provider = {status.provider: status for status in statuses}

    assert statuses_by_provider[ReviewExportProvider.ENCORD].availability == (
        ProviderAvailability.CONFIGURED
    )
    assert statuses_by_provider[ReviewExportProvider.ENCORD].detail == (
        "Encord credentials are configured; export can be attempted through "
        "the Encord scaffold."
    )


async def test_encord_exporter_marks_sample_unavailable_without_project() -> None:
    requests: list[EncordReviewExportRequest] = []

    async def export_sample(
        request: EncordReviewExportRequest,
    ) -> EncordReviewExportResult:
        requests.append(request)
        return EncordReviewExportResult(provider_sample_id="encord-sample-1")

    exporter = build_encord_review_exporter(
        client=export_sample,
        project_id=None,
    )

    exported_sample = await exporter(make_review_sample())

    assert exported_sample.export_status == ExportStatus.EXPORT_UNAVAILABLE
    assert exported_sample.incident_id == make_review_sample().incident_id
    assert requests == []


async def test_encord_exporter_marks_sample_exported_after_provider_call() -> None:
    requests: list[EncordReviewExportRequest] = []

    async def export_sample(
        request: EncordReviewExportRequest,
    ) -> EncordReviewExportResult:
        requests.append(request)
        return EncordReviewExportResult(provider_sample_id="encord-sample-1")

    exporter = build_encord_review_exporter(
        client=export_sample,
        project_id="encord-project",
    )

    exported_sample = await exporter(make_review_sample())

    assert exported_sample.export_status == ExportStatus.EXPORTED
    assert len(requests) == 1
    assert requests[0].project_id == "encord-project"
    assert requests[0].incident_id == make_review_sample().incident_id
    assert requests[0].labels == ["blocked_robot_workcell", "verified_clear"]

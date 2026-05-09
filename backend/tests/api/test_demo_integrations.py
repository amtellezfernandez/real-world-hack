from pathlib import Path

from sitewalk.api.routes.demo_integrations import (
    resolve_upload_image_path,
    write_data_url_image,
)


def test_write_data_url_image_materializes_a_real_file(tmp_path: Path) -> None:
    data_url = (
        "data:image/png;base64,"
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="
    )

    output_path = write_data_url_image(temp_dir=tmp_path, data_url=data_url, role="before")

    assert output_path.exists()
    assert output_path.suffix == ".png"
    assert output_path.read_bytes() != b""


def test_resolve_upload_image_path_prefers_data_url_over_path(tmp_path: Path) -> None:
    data_url = "data:image/jpeg;base64,aGVsbG8="
    path = tmp_path / "existing.png"
    path.write_bytes(b"existing")

    resolved = resolve_upload_image_path(
        data_url=data_url,
        path=str(path),
        temp_dir=tmp_path,
        role="after",
    )

    assert resolved is not None
    assert resolved != path
    assert resolved.exists()

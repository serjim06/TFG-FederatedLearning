import io
import json
from pathlib import Path

import pytest
from pypdf import PdfReader

import src.projects.reports as reports


@pytest.fixture
def sample_results() -> str:
    path = Path(__file__).resolve().parent / "sample_results.json"
    return path.read_text(encoding="utf-8")


@pytest.fixture
def sample_regression() -> str:
    path = Path(__file__).resolve().parent / "sample_regression.json"
    return path.read_text(encoding="utf-8")


def test_generate_report(sample_results: str) -> None:
    buffer = io.BytesIO()
    reports.generate_report(
        project_id="test_project",
        project_name="Test Project",
        project_description="Test Description",
        num_rounds=10,
        project_type="classification",
        data=sample_results,
        path=buffer,
    )
    pdf_out = buffer.getvalue()
    assert len(pdf_out) > 0
    assert pdf_out.startswith(b"%PDF-")


def test_classification_report_content(sample_results: str) -> None:
    buffer = io.BytesIO()
    reports.generate_report(
        project_id="test_project",
        project_name="Test Project",
        project_description="Test Description",
        num_rounds=10,
        project_type="classification",
        data=sample_results,
        path=buffer,
    )
    reader = PdfReader(io.BytesIO(buffer.getvalue()))
    assert len(reader.pages) >= 1
    text = reader.pages[0].extract_text()
    assert text is not None
    assert "Test Project" in text
    assert "Test Description" in text
    assert "10" in text
    assert "classification" in text
    res = json.loads(sample_results)
    cfg = res[0]["config"]
    assert str(cfg["strategy"]) in text
    assert str(cfg["epochs"]) in text
    assert str(cfg["batch_size"]) in text
    assert str(cfg["learning_rate"]) in text
    assert str(cfg["optimizer"]) in text
    assert str(cfg["loss"]) in text
    assert str(cfg["classes"]) in text


def test_regression_report_content(sample_regression: str) -> None:
    buffer = io.BytesIO()
    reports.generate_report(
        project_id="test_project",
        project_name="Test Project",
        project_description="Test Description",
        num_rounds=10,
        project_type="regression",
        data=sample_regression,
        path=buffer,
    )
    reader = PdfReader(io.BytesIO(buffer.getvalue()))
    assert len(reader.pages) >= 1
    text = reader.pages[0].extract_text()
    assert text is not None
    assert "Test Project" in text
    assert "regression" in text
    res = json.loads(sample_regression)
    cfg = res[0]["config"]
    assert str(cfg["strategy"]) in text
    assert str(cfg["loss"]) in text


def test_invalid_report_type(sample_results: str) -> None:
    buffer = io.BytesIO()
    with pytest.raises(ValueError, match="Invalid report type"):
        reports.generate_report(
            project_id="test_project",
            project_name="Test Project",
            project_description="Test Description",
            num_rounds=10,
            project_type="invalid",
            data=sample_results,
            path=buffer,
        )


def test_generate_report_rejects_empty_payload() -> None:
    buffer = io.BytesIO()
    with pytest.raises(ValueError, match="No data to generate report"):
        reports.generate_report(
            project_id="p",
            project_name="N",
            project_description="D",
            num_rounds=1,
            project_type="classification",
            data="[]",
            path=buffer,
        )
